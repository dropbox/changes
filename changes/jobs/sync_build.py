from flask import current_app

from changes.config import queue
from changes.backends.jenkinds.builder import JenkinsBuilder
from changes.constants import Status
from changes.models.build import Build


@queue.job
def sync_build(build_id):
    try:
        build = Build.query.get(build_id)
        if build.status == Status.finished:
            return

        builder = JenkinsBuilder(
            app=current_app,
            base_uri=current_app.config['JENKINS_URL'],
        )
        builder.sync_build(build)

        if build.status != Status.finished:
            sync_build.delay(
                build_id=build.id,
            )
    except Exception:
        # Ensure we continue to synchronize this build as this could be a
        # temporary failure
        sync_build.delay(
            build_id=build.id,
        )
        raise
