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
        build.result = Result.aborted
        current_app.logger.exception('Unrecoverable exception syncing %s', build_id)

    build.date_modified = datetime.utcnow()
    db.session.add(build)

    # if this build isnt finished, we assume that there's still data to sync
    if build.status != Status.finished:
        queue.delay('sync_build', kwargs={
            'build_id': build.id.hex
        }, countdown=1)

    else:
        queue.delay('update_project_stats', kwargs={
            'project_id': build.project_id.hex,
        }, countdown=1)

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
