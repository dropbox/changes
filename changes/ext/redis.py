from __future__ import absolute_import

import logging
import redis

from contextlib import contextmanager
from random import random
from time import sleep

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
    def lock(self, lock_key, timeout=3, expire=None, nowait=False):
        conn = self.redis

        if expire is None:
            expire = timeout

        delay = 0.01 + random() / 10
        attempt = 0
        max_attempts = timeout / delay
        got_lock = None
        while not got_lock and attempt < max_attempts:
            got_lock = conn.set(lock_key, '', nx=True, ex=expire)
            if not got_lock:
                if nowait:
                    break
                sleep(delay)
                attempt += 1

        self.logger.info('Acquiring lock on %s', lock_key)

        if not got_lock:
            raise UnableToGetLock('Unable to fetch lock on %s' % (lock_key,))

        try:
            yield
        finally:
            self.logger.info('Releasing lock on %s', lock_key)

            try:
                conn.delete(lock_key)
            except Exception as e:
                self.logger.exception(e)

    def incr(self, key):
        self.redis.incr(key)

    def decr(self, key):
        self.redis.decr(key)


def Redis(**o):
    return Container(_Redis, o, name='redis')
