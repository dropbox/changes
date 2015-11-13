from flask import current_app

from changes.artifacts import manager
from changes.backends.base import UnrecoverableException
from changes.constants import Result
from changes.models import Artifact, JobPlan
from changes.queue.task import tracked_task


@tracked_task
def sync_artifact(artifact_id=None, **kwargs):
    """
    Downloads an artifact from jenkins.
    """
    artifact = Artifact.query.get(artifact_id)
    if artifact is None:
        return

    step = artifact.step

    if step.result == Result.aborted:
        return

    # TODO(dcramer): we eventually want to abstract the entirety of Jenkins
    # artifact syncing so that we pull files and then process them
    if artifact.file:
        try:
            manager.process(artifact)
        except Exception:
            current_app.logger.exception(
                'Unrecoverable exception processing artifact %s: %s',
                artifact.step_id, artifact)
    else:
        jobplan, implementation = JobPlan.get_build_step_for_job(job_id=step.job_id)

        try:
            implementation.fetch_artifact(artifact=artifact, sync_logs=kwargs.pop('sync_logs', False))

        except UnrecoverableException:
            current_app.logger.exception(
                'Unrecoverable exception fetching artifact %s: %s',
                artifact.step_id, artifact)
