from flask import current_app

from sqlalchemy.orm import subqueryload_all

from changes.backends.base import UnrecoverableException
from changes.constants import Status, Result
from changes.config import db
from changes.models import JobStep, JobPlan, Plan
from changes.queue.task import tracked_task


def get_build_step(job_id):
    job_plan = JobPlan.query.options(
        subqueryload_all('plan.steps')
    ).filter(
        JobPlan.job_id == job_id,
    ).join(Plan).first()
    if not job_plan:
        raise UnrecoverableException('Missing job plan for job: %s' % (job_id,))

    try:
        step = job_plan.plan.steps[0]
    except IndexError:
        raise UnrecoverableException('Missing steps for plan: %s' % (job_plan.plan.id))

    implementation = step.get_implementation()
    return implementation


@tracked_task
def sync_job_step(step_id):
    step = JobStep.query.get(step_id)
    if not step:
        return

    if step.status == Status.finished:
        return

    try:
        implementation = get_build_step(step.job_id)
        implementation.update_step(step=step)

    except UnrecoverableException:
        step.status = Status.finished
        step.result = Result.aborted
        current_app.logger.exception('Unrecoverable exception syncing step %s', step.id)

    db.session.add(step)
    db.session.commit()

    if step.status != Status.finished:
        raise sync_job_step.NotFinished
