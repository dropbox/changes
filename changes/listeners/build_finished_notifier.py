"""
A simple build-finished listener that pings registered URLs whenever a build
finishes.

The post request includes a form-encoded body with the following information:
    - build_id: The ID of the build that completed.

It's up to the receiver to fetch from Changes any information it wants to know
about the build (likely, the build status). This design allows us not to worry
about client authentication: a malicious entity can spoof the notifications,
but cannot confuse the receiver with any false information. Perhaps someday
this mechanism will be extended to carry authentication information and
additional data about the build result.
"""

import logging
import requests

from flask import current_app

from changes.models import Build


logger = logging.getLogger('build-finished-notifier')


def build_finished_handler(build_id, **kwargs):
    build = Build.query.get(build_id)
    if build is None:
        return

    # A possible improvement would be to make all of these requests in separate
    # celery tasks, for better isolation between requests to different hooks.
    for u in current_app.config.get('BUILD_FINISHED_URLS', []):
        try:
            url, verify = u
            if verify is None or not isinstance(verify, basestring):
                verify = True
        except ValueError:
            # TODO this only exists for compatibility reasons.
            # once we are sure that the config value is a list of tuples,
            # remove this.
            url = u
            verify = True
        try:
            requests.post(
                url,
                data={'build_id': build.id},
                timeout=10,

                # this is either a string path to the ca bundle or a boolean
                # indicating that the ssl cert should be checked
                verify=verify
            )
        except Exception:
            logger.exception("problem posting build finished notification")
