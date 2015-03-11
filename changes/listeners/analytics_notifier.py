"""Posts JSON with basic information for each completed build to the URL specified
in the config variable ANALYTICS_POST_URL, if that value is set.

The data posted to ANALYTICS_POST_URL will be a JSON array of objects, with each
object representing a completed build.
"""

import logging
import json
import requests
from datetime import datetime

from flask import current_app

from changes.models import Build

logger = logging.getLogger('analytics_notifier')


def _datetime_to_timestamp(dt):
    """Convert a datetime to unix epoch time in seconds."""
    return int((dt - datetime.utcfromtimestamp(0)).total_seconds())


def build_finished_handler(build_id, **kwargs):
    url = current_app.config.get('ANALYTICS_POST_URL')
    if not url:
        return
    build = Build.query.get(build_id)
    if build is None:
        return

    def maybe_ts(dt):
        if dt:
            return _datetime_to_timestamp(dt)
        return None

    data = {
        'build_id': build.id.hex,
        'result': unicode(build.result),
        'project_slug': build.project.slug,
        'is_commit': bool(build.source.is_commit()),
        'label': build.label,
        'number': build.number,
        'duration': build.duration,
        'target': build.target,
        'date_created': maybe_ts(build.date_created),
        'date_started': maybe_ts(build.date_started),
        'date_finished': maybe_ts(build.date_finished),
    }
    if build.author:
        data['author'] = build.author.email

    post_build_data(url, data)


def post_build_data(url, data):
    try:
        # NB: We send an array of JSON objects rather than a single object
        # so the interface doesn't need to change if we later want to do batch
        # posting.
        resp = requests.post(url, data=json.dumps([data]))
        resp.raise_for_status()
        # Should probably retry here so that transient failures don't result in
        # missing data.
    except Exception:
        logger.exception("Failed to post to Analytics")
