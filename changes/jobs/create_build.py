from flask import current_app

from changes.backends.jenkins.builder import JenkinsBuilder
from changes.config import queue
from changes.models import Build


def create_build(build_id):
    build = Build.query.get(build_id)
    if not build:
        return

    backend = JenkinsBuilder(
        app=current_app,
        base_url=current_app.config['JENKINS_URL'],
    )

    try:
        backend.create_build(build)
    except Exception as exc:
        current_app.logger.exception('Failed to create build %s', build_id)
        raise queue.retry('create_build', kwargs={
            'build_id': build_id,
        }, exc=exc)

    queue.delay('sync_build', kwargs={
        'build_id': build_id,
    })
