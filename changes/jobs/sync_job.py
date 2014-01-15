from datetime import datetime
from flask import current_app
from sqlalchemy.orm import subqueryload_all

from changes.backends.base import UnrecoverableException
from changes.config import db, queue
from changes.constants import Status, Result
from changes.events import publish_job_update
from changes.models import Job, JobPlan, Plan
from changes.queue.task import tracked_task


@tracked_task
def sync_job(job_id):
    job = Job.query.get(job_id)
    if not job:
        return

    if job.status == Status.finished:
        return

    # TODO(dcramer): we make an assumption that there is a single step
    job_plan = JobPlan.query.options(
        subqueryload_all('plan.steps')
    ).filter(
        JobPlan.job_id == job.id,
    ).join(Plan).first()
    try:
        if not job_plan:
            raise UnrecoverableException('Got sync_job task without job plan: %s' % (job.id,))

        try:
            step = job_plan.plan.steps[0]
        except IndexError:
            raise UnrecoverableException('Missing steps for plan')

        implementation = step.get_implementation()
        implementation.execute(job=job)

    except UnrecoverableException:
        job.status = Status.finished
        job.result = Result.aborted
        current_app.logger.exception('Unrecoverable exception syncing %s', job.id)

    current_datetime = datetime.utcnow()

    job.date_modified = current_datetime

    db.session.add(job)
    db.session.commit()

    publish_job_update(job)

    if job.status != Status.finished:
        raise sync_job.NotFinished

    queue.delay('notify_listeners', kwargs={
        'job_id': job.id.hex,
        'signal_name': 'job.finished',
    })

    if job_plan:
        queue.delay('update_project_plan_stats', kwargs={
            'project_id': job.project_id.hex,
            'plan_id': job_plan.plan_id.hex,
        }, countdown=1)
