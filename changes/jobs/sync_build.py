from datetime import datetime
from flask import current_app

from changes.backends.jenkins.builder import JenkinsBuilder
from changes.config import db, queue
from changes.constants import Status, Result
from changes.models import Build, RemoteEntity


def sync_build(build_id):
    try:
        build = Build.query.get(build_id)
        if not build:
            return

        if build.status == Status.finished:
            return

        # HACK(dcramer): this definitely is a temporary fix for our "things are
        # only a single builder" problem
        entity = RemoteEntity.query.filter_by(
            provider='jenkins',
            internal_id=build.id,
            type='build',
        ).first()
        if not entity:
            build.status = Status.finished
            build.result = Result.aborted
        else:
            builder = JenkinsBuilder(
                app=current_app,
                base_url=current_app.config['JENKINS_URL'],
            )
            builder.sync_build(build)

        build.date_modified = datetime.utcnow()
        db.session.add(build)

        if build.status != Status.finished:
            queue.delay('sync_build', build_id=build.id.hex)
    except Exception:
        # Ensure we continue to synchronize this build as this could be a
        # temporary failure
        queue.retry('sync_build', build_id=build.id.hex)
        raise
