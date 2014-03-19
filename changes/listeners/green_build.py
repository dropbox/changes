import logging
import requests

from flask import current_app

from changes.config import db
from changes.constants import Result
from changes.models import ProjectOption, RepositoryBackend
from changes.utils.http import build_uri

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


def build_finished_handler(build, **kwargs):
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

    # we only want to identify stable revisions
    if build.patch_id or not build.revision_sha:
        logger.debug('Ignoring build due to non-commit: %s', build.id)
        return

    options = get_options(build.project_id)

    if options.get('green-build.notify', '1') != '1':
        logger.info('green-build.notify disabled for project: %s', build.project_id)
        return

    if build.repository.backend != RepositoryBackend.hg:
        logger.info('Repository backend is not supported: %s', build.repository.id)
        return

    vcs = build.repository.get_vcs()
    if vcs is None:
        logger.info('Repository has no VCS set: %s', build.repository.id)
        return

    # ensure we have the latest changes
    vcs.update()

    release_id = vcs.run(['log', '-r %s' % (build.revision_sha,), '--limit=1', '--template={rev}:{node|short}'])

    project = options.get('green-build.project') or build.project.slug

    requests.post(url, auth=auth, data={
        'project': project,
        'id': release_id,
        'build_url': build_uri('/projects/{0}/builds/{1}/'.format(
            build.project.slug, build.id.hex)),
        'build_server': 'changes',
    })
