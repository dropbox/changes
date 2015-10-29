from flask import current_app
from functools import wraps
from hashlib import md5

from changes.ext.redis import UnableToGetLock
from changes.config import redis


def lock(func):
    @wraps(func)
    def wrapped(**kwargs):
        key = '{0}:{1}:{2}'.format(
            func.__module__,
            func.__name__,
            md5(
                '&'.join('{0}={1}'.format(k, repr(v))
                for k, v in sorted(kwargs.iteritems()))
            ).hexdigest()
        )
        try:
            with redis.lock(key, expire=300, nowait=True):
                return func(**kwargs)
        except UnableToGetLock:
            current_app.logger.warn('Unable to get lock for %s', key)

    return wrapped
