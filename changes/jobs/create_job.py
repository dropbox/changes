from flask import current_app

from changes.backends.base import UnrecoverableException
from changes.config import db
from changes.constants import Status, Result
from changes.jobs.sync_job import sync_job
from changes.models import Job, JobPlan
from changes.queue.task import tracked_task


def abort_create(task):
    job = Job.query.get(task.kwargs['job_id'])
    job.status = Status.finished
    job.result = Result.aborted
    db.session.add(job)
    db.session.commit()
    current_app.logger.exception('Unrecoverable exception creating job %s', job.id)


@tracked_task(on_abort=abort_create, max_retries=10)
def create_job(job_id):
    job = Job.query.get(job_id)
    if not job:
        return

    # we might already be marked as finished for various reasons
    # (such as aborting the task)
    if job.status == Status.finished:
        return

    jobplan, implementation = JobPlan.get_build_step_for_job(job_id=job.id)
    if implementation is None:
        # TODO(dcramer): record a FailureReason?
        job.status = Status.finished
        job.result = Result.failed
        current_app.logger.exception('No build plan set %s', job_id)
        return

    try:
        implementation.execute(job=job)
    except UnrecoverableException:
        job.status = Status.finished
        job.result = Result.aborted
        current_app.logger.exception('Unrecoverable exception creating %s', job_id)
        return

    sync_job.delay(
        job_id=job.id.hex,
        task_id=job.id.hex,
        parent_task_id=job.build_id.hex,
    )
