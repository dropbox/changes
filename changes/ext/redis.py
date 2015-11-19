from __future__ import absolute_import

import logging
import redis
import time

from contextlib import contextmanager
from random import random

from .container import Container


class UnableToGetLock(Exception):
    pass


class _Redis(object):

    def __init__(self, app, options):
        self.app = app
        self.redis = redis.from_url(app.config['REDIS_URL'])
        self.logger = logging.getLogger(app.name + '.redis')
        # TODO(kylec): Version check to fail early if we're connected to a
        # redis-server that doesn't support the operations we use.

    def __getattr__(self, name):
        return getattr(self.redis, name)

    @contextmanager
    def lock(self, lock_key, expire=None, blocking_timeout=3, nowait=False):
        """
        Returns a context for locking a redis lock with the given key

        Args:
            lock_key (string): key to lock
            expire (float): how long (in seconds) we can hold lock before it is
                            automatically released
            blocking_timeout (float): how long (in seconds) to try locking until we give up.
            nowait (bool): if True, don't block if can't acquire the lock
                           (will instead raise an exception)
        """
        conn = self.redis

        if expire is None:
            expire = blocking_timeout

        delay = 0.01 + random() / 10
        lock = conn.lock(lock_key, timeout=expire, sleep=delay)
        acquired = lock.acquire(blocking=not nowait, blocking_timeout=blocking_timeout)
        # This is likely slightly after it was actually acquired, but it avoids reporting blocked
        # time as time spent holding the lock.
        start = time.time()

        self.logger.info('Acquiring lock on %s', lock_key)

        if not acquired:
            raise UnableToGetLock('Unable to fetch lock on %s' % (lock_key,))

        try:
            yield
        finally:
            self.logger.info('Releasing lock on %s', lock_key)

            try:
                lock.release()
            except Exception:
                # notably, an exception is raised if we release a lock we don't
                # own, e.g. because it expired while we held it.
                self.logger.exception("Error releasing lock %s acquired around %ss ago", lock_key, time.time() - start)

    def incr(self, key):
        self.redis.incr(key)

    def decr(self, key):
        self.redis.decr(key)


def Redis(**o):
    return Container(_Redis, o, name='redis')
