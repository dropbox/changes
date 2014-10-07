import logging

from flask import current_app
from phabricator import Phabricator

from changes.config import db
from changes.constants import Result
from changes.models import Build, ProjectOption
from changes.utils.http import build_uri

logger = logging.getLogger('phabricator-listener')
PHABRICATOR = None


def get_options(project_id):
    return dict(
        db.session.query(
            ProjectOption.name, ProjectOption.value
        ).filter(
            ProjectOption.project_id == project_id,
            ProjectOption.name.in_([
                'phabricator.notify'
            ])
        )
    )


def _init_phabricator():
    global PHABRICATOR
    if not PHABRICATOR:
        host = current_app.config.get('PHABRICATOR_HOST')
        username = current_app.config.get('PHABRICATOR_USERNAME')
        cert = current_app.config.get('PHABRICATOR_CERT')

        PHABRICATOR = Phabricator(username, cert, host)
        PHABRICATOR.connect()
        whoami = PHABRICATOR.user.whoami()
        logger.info("Connected to tails as {username}.".format(username=whoami['userName']))

    return PHABRICATOR


def build_finished_handler(build_id, **kwargs):
    if not current_app.config.get('PHABRICATOR_POST_BUILD_RESULT'):
        return

    build = Build.query.get(build_id)
    if build is None:
        return

    if build.source.patch_id:
        return

    if build.result not in (Result.failed, Result.passed):
        return

    options = get_options(build.project_id)
    if options.get('phabricator.notify', '0') != '1':
        return

    message = u'Build {result} - {project} #{number} ({target}). Build Results: [link]({link})'.format(
        number='{0}'.format(build.number),
        result=unicode(build.result),
        target=build.target or build.source.revision_sha or 'Unknown',
        project=build.project.name,
        link=build_uri('/projects/{0}/builds/{1}/'.format(build.project.slug, build.id.hex))
    )

    if build.author:
        message += ' - {author}'.format(author=build.author.email,)

    post_comment(build.target, message)


def post_comment(target, message):
    try:
        if not target.startswith(u'D') or len(target) < 2:
            logging.error("Invalid phabricator target %s" % target)

        revision_id = target[1:]
        phab = _init_phabricator()
        phab.differential.createcomment(revision_id=revision_id, message=message)
    except Exception:
        logger.exception("Failed to post to target: %s" % target)
