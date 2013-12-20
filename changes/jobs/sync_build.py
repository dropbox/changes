from datetime import datetime
from flask import current_app
from sqlalchemy.orm import subqueryload_all
import sys
import warnings

from changes.backends.base import UnrecoverableException
from changes.backends.jenkins.builder import JenkinsBuilder
from changes.config import db, queue
from changes.constants import Status, Result
from changes.models import Build, BuildPlan, Plan, Project, RemoteEntity
from changes.utils.locking import lock


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


def _sync_build(build_id):
    build = Build.query.get(build_id)
    if not build:
        return

    if build.status == Status.finished:
        return

    # TODO(dcramer): we make an assumption that there is a single step
    build_plan = BuildPlan.query.options(
        subqueryload_all('plan.steps')
    ).filter(
        BuildPlan.build_id == build.id,
    ).join(Plan).first()

    try:

        if not build_plan:
            # TODO(dcramer): once we migrate to build plans we can remove this
            warnings.warn(
                'Got sync_build task without build plan: %s' % (build_id,))
            sync = sync_with_builder
        else:
            try:
                step = build_plan.plan.steps[0]
            except IndexError:
                raise UnrecoverableException('Missing steps for plan')

            implementation = step.get_implementation()
            sync = implementation.sync

        sync(build=build)

    except UnrecoverableException:
        build.status = Status.finished
        build.result = Result.unknown
        current_app.logger.exception('Unrecoverable exception syncing %s', build_id)

    build.date_modified = datetime.utcnow()
    db.session.add(build)

    # if this build isnt finished, we assume that there's still data to sync
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


@lock
def sync_build(build_id):
    try:
        _sync_build(build_id)

    except Exception:
        # Ensure we continue to synchronize this build as this could be a
        # temporary failure
        current_app.logger.exception('Failed to sync build %s', build_id)
        raise queue.retry('sync_build', kwargs={
            'build_id': build_id,
        }, exc=sys.exc_info(), countdown=60)
