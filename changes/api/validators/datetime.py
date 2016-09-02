from __future__ import absolute_import

from datetime import datetime

import logging

# We appear to be hitting https://bugs.python.org/issue7980, but by using
# strptime early on, the race should be avoided.
datetime.strptime("", "")


class ISODatetime(object):
    def __call__(self, value):
        # type: (str) -> datetime
        try:
            return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ')
        except Exception:
            logging.exception("Failed to parse datetime: %s", value)
            raise ValueError('Datetime was not parseable. Expected ISO 8601 with timezone: YYYY-MM-DDTHH:MM:SS.mmmmmmZ')
