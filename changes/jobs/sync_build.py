from datetime import datetime
from flask import current_app

from changes.backends.jenkins.builder import JenkinsBuilder
from changes.config import db, queue
from changes.constants import Status, Result
from changes.models import Build, Project, RemoteEntity


def sync_with_builder(build):
    build.date_modified = datetime.utcnow()
    db.session.add(build)

    entity = RemoteEntity.query.filter_by(
        provider='jenkins',
        internal_id=build.id,
        type='build',
    ).first()
    if not entity:
        queue.delay('create_build', kwargs={
            'build_id': build.id.hex,
        }, countdown=5)
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
            last_5_builds = list(Build.query.filter_by(
                result=Result.passed,
                status=Status.finished,
                project_id=build.project_id,
            ).order_by(Build.date_finished.desc())[:5])
            if last_5_builds:
                avg_build_time = sum(
                    b.duration for b in last_5_builds
                    if b.duration
                ) / len(last_5_builds)
            else:
                avg_build_time = None

            db.session.query(Project).filter(
                Project.id == build.project_id
            ).update({
                Project.avg_build_time: avg_build_time,
            }, synchronize_session=False)

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
