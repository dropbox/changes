import logging
import time
import hashlib
import json
import requests

from flask import current_app

from changes.config import db
from changes.constants import Result
from changes.models import Build, ProjectOption
from changes.utils.http import build_uri

logger = logging.getLogger('phabricator-listener')


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


def post_diff_comment(diff_id, comment):
    user = current_app.config.get('PHABRICATOR_USERNAME')
    host = current_app.config.get('PHABRICATOR_HOST')
    cert = current_app.config.get('PHABRICATOR_CERT')

    if not cert:
        logger.error("Couldn't find phabricator credentials user: %s host: %s cert: %s",
                     user, host, cert)
        return

    token = int(time.time())

    connect_args = {
        'authSignature': hashlib.sha1(str(token) + cert).hexdigest(),
        'authToken': token,
        'client': 'changes-phabricator',
        'clientVersion': 1,
        'host': host,
        'user': user,
    }

    connect_url = "%s/api/conduit.connect" % host
    resp = requests.post(connect_url, {
        '__conduit__': True,
        'output': 'json',
        'params': json.dumps(connect_args),
    })

    resp = json.loads(resp.content)['result']
    auth_params = {
        'connectionID': resp['connectionID'],
        'sessionKey': resp['sessionKey'],
    }

    comment_args = {
        'params': json.dumps({
            'revision_id': diff_id,
            'message': comment,
            '__conduit__': auth_params,
        }),
        'output': 'json',
    }

    comment_url = "%s/api/differential.createcomment" % host
    requests.post(comment_url, comment_args)


def build_finished_handler(build_id, **kwargs):
    build = Build.query.get(build_id)
    if build is None:
        return

    target = build.target
    is_diff_build = target and target.startswith(u'D')
    if not is_diff_build:
        # Not a diff build
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

    post_comment(target, message)


def post_comment(target, message):
    try:
        logger.info("Posting build results to %s", target)
        revision_id = target[1:]
        post_diff_comment(revision_id, message)
    except Exception:
        logger.exception("Failed to post to target: %s", target)
