from flask import current_app
from functools import wraps

from changes.config import redis


def lock(func):
    @wraps(func)
    def wrapped(**kwargs):
        key = '{0}:{1}'.format(
            func.__name__,
            '&'.join('{0}={1}'.format(k, v)
            for k, v in sorted(kwargs.iteritems()))
        )
        try:
            with redis.lock(key, timeout=1, expire=300, nowait=True):
                return func(**kwargs)
        except redis.UnableToGetLock:
            current_app.logger.warn('Unable to get lock for %s', key)

    return wrapped
