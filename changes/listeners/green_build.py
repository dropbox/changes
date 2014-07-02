import logging
import requests

from datetime import datetime
from flask import current_app
from time import time

from changes.config import db
from changes.constants import Result
from changes.db.utils import create_or_update
from changes.models import (
    Build, Event, EventType, ProjectOption, RepositoryBackend
)
from changes.utils.http import build_uri
from changes.utils.locking import lock

logger = logging.getLogger('green_build')


def get_options(project_id):
    return dict(
        db.session.query(
            ProjectOption.name, ProjectOption.value
        ).filter(
            ProjectOption.project_id == project_id,
            ProjectOption.name.in_([
                'green-build.notify', 'green-build.project',
            ])
        )
    )


@lock
def build_finished_handler(build_id, **kwargs):
    build = Build.query.get(build_id)
    if build is None:
        return

    if build.result != Result.passed:
        return

    url = current_app.config.get('GREEN_BUILD_URL')
    if not url:
        logger.info('GREEN_BUILD_URL not set')
        return

    auth = current_app.config['GREEN_BUILD_AUTH']
    if not auth:
        logger.info('GREEN_BUILD_AUTH not set')
        return

    source = build.source

    # we only want to identify stable revisions
    if not source.is_commit():
        logger.debug('Ignoring build due to non-commit: %s', build.id)
        return

    options = get_options(build.project_id)

    if options.get('green-build.notify', '1') != '1':
        logger.info('green-build.notify disabled for project: %s', build.project_id)
        return

    vcs = source.repository.get_vcs()
    if vcs is None:
        logger.info('Repository has no VCS set: %s', source.repository.id)
        return

    # ensure we have the latest changes
    if vcs.exists():
        vcs.update()
    else:
        vcs.clone()

    # green_build requires an identifier that is <integer:revision_sha>
    # the integer must also be sequential and unique
    # TODO(dcramer): it's a terrible API and realistically we should just be
    # sending a sha, as the sequential counter is hg-only, invalid, and really
    # isn't used
    if source.repository.backend == RepositoryBackend.hg:
        release_id = vcs.run(['log', '-r %s' % (source.revision_sha,), '--limit=1', '--template={rev}:{node|short}'])
    else:
        release_id = '%d:%s' % (time(), source.revision_sha)

    project = options.get('green-build.project') or build.project.slug

    logging.info('Making green_build request to %s', url)
    try:
        requests.post(url, auth=auth, data={
            'project': project,
            'id': release_id,
            'build_url': build_uri('/projects/{0}/builds/{1}/'.format(
                build.project.slug, build.id.hex)),
            'build_server': 'changes',
        })
    except Exception:
        logger.exception('Failed to report green build')
        status = 'fail'
    else:
        status = 'success'

    create_or_update(Event, where={
        'type': EventType.green_build,
        'item_id': build.id,
    }, values={
        'data': {
            'status': status,
        },
        'date_modified': datetime.utcnow(),
    })
