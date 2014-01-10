import sys

from flask import current_app
from sqlalchemy.orm import subqueryload_all

from changes.backends.base import UnrecoverableException
from changes.config import queue
from changes.constants import Status, Result
from changes.db.utils import get_or_create
from changes.models import Job, JobPlan, Plan, Task
from changes.utils.locking import lock


@lock
def create_job(job_id):
    job = Job.query.get(job_id)
    if not job:
        return

    task, task_created = get_or_create(Task, where={
        'task_name': 'sync_job',
        'parent_id': job.build_id,
        'child_id': job.id,
    })

    job_plan = JobPlan.query.options(
        subqueryload_all('plan.steps')
    ).filter(
        JobPlan.job_id == job.id,
    ).join(Plan).first()

    try:
        if not job_plan:
            raise UnrecoverableException('Got create_job task without job plan: %s' % (job_id,))
        try:
            step = job_plan.plan.steps[0]
        except IndexError:
            raise UnrecoverableException('Missing steps for plan')

        implementation = step.get_implementation()
        implementation.execute(job=job)

    except UnrecoverableException:
        job.status = Status.finished
        job.result = Result.aborted
        current_app.logger.exception('Unrecoverable exception creating %s', job_id)
        return

    except Exception:
        current_app.logger.exception('Failed to create job %s', job_id)
        raise queue.retry('create_job', kwargs={
            'job_id': job_id,
        }, exc=sys.exc_info())

    # this should always be true, but for consistency we want to enforce the
    # same constraints throughout the task management
    if task_created:
        queue.delay('sync_job', kwargs={
            'job_id': job_id,
        }, countdown=5)
