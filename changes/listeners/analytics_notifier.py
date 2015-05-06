"""Posts JSON with basic information for each completed build to the URL specified
in the config variable ANALYTICS_POST_URL, if that value is set.

The data posted to ANALYTICS_POST_URL will be a JSON array of objects, with each
object representing a completed build.
"""

import logging
import json
import re
import requests
from sqlalchemy import distinct
from datetime import datetime

from flask import current_app

from changes.config import db
from changes.models import Build, FailureReason

logger = logging.getLogger('analytics_notifier')


def _datetime_to_timestamp(dt):
    """Convert a datetime to unix epoch time in seconds."""
    return int((dt - datetime.utcfromtimestamp(0)).total_seconds())


_REV_URL_RE = re.compile(r'^\s*Differential Revision:\s+(http.*/D[0-9]+)\s*$', re.MULTILINE)


def _get_phabricator_revision_url(build):
    """Returns the Phabricator Revision URL for a Build.

    Args:
      build (Build): The Build.

    Returns:
      A str with the Phabricator Revision URL, or None if we couldn't find one (or found
      multiple).
    """
    source_data = build.source.data or {}
    rev_url = source_data.get('phabricator.revisionURL')
    if rev_url:
        return rev_url
    if build.message:
        matches = _REV_URL_RE.findall(build.message)
        # only return if there's a clear choice.
        if matches and len(matches) == 1:
            return matches[0]
    return None


def _get_failure_reasons(build):
    """Return the names of all the FailureReasons associated with a build.
    Args:
        build (Build): The build to return reasons for.
    Returns:
        list: A sorted list of the distinct FailureReason.reason values associated with
        the build.
    """
    failure_reasons = [r for r, in db.session.query(
                distinct(FailureReason.reason)
            ).filter(
                FailureReason.build_id == build.id
            ).all()]
    # The order isn't particularly meaningful; the sorting is primarily
    # to make the same set of reasons reliably result in the same JSON.
    return sorted(failure_reasons)


def build_finished_handler(build_id, **kwargs):
    url = current_app.config.get('ANALYTICS_POST_URL')
    if not url:
        return
    build = Build.query.get(build_id)
    if build is None:
        return

    failure_reasons = _get_failure_reasons(build)

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
        # Revision URL rather than just revision id because the URL should
        # be globally unique, whereas the id is only certain to be unique for
        # a single Phabricator instance.
        'phab_revision_url': _get_phabricator_revision_url(build),
        'failure_reasons': failure_reasons,
    }
    if build.author:
        data['author'] = build.author.email

    post_build_data(url, data)


def post_build_data(url, data):
    try:
        # NB: We send an array of JSON objects rather than a single object
        # so the interface doesn't need to change if we later want to do batch
        # posting.
        resp = requests.post(url, headers={'Content-Type': 'application/json'}, data=json.dumps([data]))
        resp.raise_for_status()
        # Should probably retry here so that transient failures don't result in
        # missing data.
    except Exception:
        logger.exception("Failed to post to Analytics")
