from flask import current_app

from changes.backends.base import UnrecoverableException
from changes.config import db
from changes.constants import Status, Result
from changes.jobs.sync_job import sync_job
from changes.models import Job, JobPlan, ProjectStatus
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
    pass
