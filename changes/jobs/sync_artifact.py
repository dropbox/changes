from flask import current_app

from changes.backends.jenkins.builder import JenkinsBuilder
from changes.config import queue
from changes.models import Job


def sync_with_builder(job, artifact):
    # HACK(dcramer): this definitely is a temporary fix for our "things are
    # only a single builder" problem
    builder = JenkinsBuilder(
        app=current_app,
        base_url=current_app.config['JENKINS_URL'],
    )
    builder.sync_artifact(job, artifact)


def sync_artifact(job_id, artifact):
    try:
        job = Job.query.get(job_id)
        if not job:
            return

        sync_with_builder(job)

    except Exception as exc:
        # Ensure we continue to synchronize this job as this could be a
        # temporary failure
        current_app.logger.exception(
            'Failed to sync artifact %r, %r', job_id, artifact)
        raise queue.retry('sync_artifact', kwargs={
            'job_id': job_id,
            'artifact': artifact,
        }, exc=exc, countdown=60)
