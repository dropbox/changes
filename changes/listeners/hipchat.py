import json
import logging
import requests

from flask import current_app

from changes.config import db
from changes.constants import Result, Status
from changes.models import Build, ProjectOption, Source
from changes.utils.http import build_uri

logger = logging.getLogger('hipchat')

DEFAULT_TIMEOUT = 1
API_ENDPOINT = 'https://api.hipchat.com/v1/rooms/message'


def get_options(project_id):
    return dict(
        db.session.query(
            ProjectOption.name, ProjectOption.value
        ).filter(
            ProjectOption.project_id == project_id,
            ProjectOption.name.in_([
                'hipchat.notify', 'hipchat.room',
            ])
        )
    )


def should_notify(build):
    if build.result not in (Result.failed, Result.passed):
        return

    parent = Build.query.join(
        Source, Source.id == Build.source_id,
    ).filter(
        Source.patch_id == None,  # NOQA
        Source.revision_sha != build.source.revision_sha,
        Build.project == build.project,
        Build.date_created < build.date_created,
        Build.status == Status.finished,
        Build.result.in_([Result.passed, Result.failed]),
    ).order_by(Build.date_created.desc()).first()

    if parent is None:
        return build.result == Result.failed

    if parent.result == build.result:
        return False

    return True


def build_finished_handler(build_id, **kwargs):
    build = Build.query.get(build_id)
    if build is None:
        return

    if build.patch_id:
        return

    if not current_app.config.get('HIPCHAT_TOKEN'):
        return

    if not should_notify(build):
        return

    options = get_options(build.project_id)

    if options.get('hipchat.notify', '0') != '1':
        return

    if not options.get('hipchat.room'):
        return

    message = u'Build {result} - <a href="{link}">{project} #{number}</a> ({target})'.format(
        number='{0}'.format(build.number),
        result=unicode(build.result),
        target=build.target or build.source.revision_sha or 'Unknown',
        project=build.project.name,
        link=build_uri('/projects/{0}/builds/{1}/'.format(
            build.project.slug, build.id.hex))
    )
    if build.author:
        message += ' - {author}'.format(
            author=build.author.email,
        )

    send_payload(
        token=current_app.config['HIPCHAT_TOKEN'],
        room=options['hipchat.room'],
        message=message,
        notify=True,
        color='green' if build.result == Result.passed else 'red',
    )


def send_payload(token, room, message, notify, color='red',
                 timeout=DEFAULT_TIMEOUT):
    data = {
        'auth_token': token,
        'room_id': room,
        'from': 'Changes',
        'message': message,
        'notify': int(notify),
        'color': color,
    }
    response = requests.post(API_ENDPOINT, data=data, timeout=timeout)
    response_data = json.loads(response.content)

    if 'status' not in response_data:
        logger.error('Unexpected response: %s', response_data)

    if response_data['status'] != 'sent':
        logger.error('Event could not be sent to hipchat')
