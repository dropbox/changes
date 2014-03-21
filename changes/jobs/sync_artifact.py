from flask import current_app

from sqlalchemy.orm import subqueryload_all

from changes.backends.base import UnrecoverableException
from changes.models import Artifact, JobPlan, Plan
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
def sync_artifact(artifact_id=None):
    if artifact_id:
        artifact = Artifact.query.get(artifact_id)

    if artifact is None:
        return

    step = artifact.step
    data = artifact.data

    try:
        implementation = get_build_step(step.job_id)
        implementation.fetch_artifact(step=step, artifact=data)

    except UnrecoverableException:
        current_app.logger.exception(
            'Unrecoverable exception fetching artifact %s: %s',
            step.id, artifact)
