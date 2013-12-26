import sys

from flask import current_app
from sqlalchemy.orm import subqueryload_all

from changes.backends.base import UnrecoverableException
from changes.backends.jenkins.builder import JenkinsBuilder
from changes.config import queue
from changes.constants import Status, Result
from changes.models import Job, JobPlan, Plan
from changes.utils.locking import lock


@lock
def create_build(build_id):
    job = Job.query.get(build_id)
    if not job:
        return

    job_plan = JobPlan.query.options(
        subqueryload_all('plan.steps')
    ).filter(
        JobPlan.job_id == job.id,
    ).join(Plan).first()

    try:
        if not job_plan:
            # TODO(dcramer): once we migrate to job plans we can remove this
            current_app.logger.warning(
                'Got create_build task without job plan: %s', build_id)

            backend = JenkinsBuilder(
                app=current_app,
                base_url=current_app.config['JENKINS_URL'],
            )
            create_job = backend.create_job
        else:
            try:
                step = job_plan.plan.steps[0]
            except IndexError:
                raise UnrecoverableException('Missing steps for plan')

            implementation = step.get_implementation()
            create_job = implementation.execute

        create_job(job=job)

    except UnrecoverableException:
        job.status = Status.finished
        job.result = Result.aborted
        current_app.logger.exception('Unrecoverable exception creating %s', build_id)
        return

    except Exception:
        current_app.logger.exception('Failed to create job %s', build_id)
        raise queue.retry('create_build', kwargs={
            'build_id': build_id,
        }, exc=sys.exc_info())

    queue.delay('sync_build', kwargs={
        'build_id': build_id,
    }, countdown=5)
