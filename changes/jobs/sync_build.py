from datetime import datetime
from flask import current_app

from changes.backends.jenkins.builder import JenkinsBuilder
from changes.config import db, queue
from changes.constants import Status, Result
from changes.models import Build, RemoteEntity


def sync_with_builder(build):
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


def sync_build(build_id):
    try:
        build = Build.query.get(build_id)
        if not build:
            return

        if build.status == Status.finished:
            return

        sync_with_builder(build)

        build.date_modified = datetime.utcnow()
        db.session.add(build)

        if build.status != Status.finished:
            queue.delay('sync_build', kwargs={
                'build_id': build.id.hex
            }, countdown=1)
        else:
            queue.delay('notify_listeners', kwargs={
                'build_id': build.id.hex,
                'signal_name': 'build.finished',
            })

    except Exception as exc:
        # Ensure we continue to synchronize this build as this could be a
        # temporary failure
        current_app.logger.exception('Failed to sync build %s', build_id)
        raise queue.retry('sync_build', kwargs={
            'build_id': build_id,
        }, exc=exc, countdown=60)
