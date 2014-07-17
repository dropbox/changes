from __future__ import absolute_import, print_function

from datetime import datetime


class ISODatetime(object):
    def __call__(self, value):
        try:
            return datetime.strptime(value, '%Y-%m-%dT%H:%M:%S.%fZ')
        except Exception:
            raise ValueError('Datetime was not parseable. Expected ISO 8601 with timezone: YYYY-MM-DDTHH:MM:SS.mmmmmmZ')
