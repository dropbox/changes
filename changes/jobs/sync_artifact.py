from flask import current_app

from changes.backends.jenkins.builder import JenkinsBuilder
from changes.config import queue
from changes.models import Build


def sync_with_builder(build, artifact):
    # HACK(dcramer): this definitely is a temporary fix for our "things are
    # only a single builder" problem
    builder = JenkinsBuilder(
        app=current_app,
        base_url=current_app.config['JENKINS_URL'],
    )
    builder.sync_artifact(build, artifact)


def sync_artifact(build_id, artifact):
    try:
        build = Build.query.get(build_id)
        if not build:
            return

        sync_with_builder(build)

    except Exception as exc:
        # Ensure we continue to synchronize this build as this could be a
        # temporary failure
        current_app.logger.exception(
            'Failed to sync artifact %r, %r', build_id, artifact)
        raise queue.retry('sync_artifact', kwargs={
            'build_id': build_id,
            'artifact': artifact,
        }, exc=exc, countdown=60)
