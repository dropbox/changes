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
    UnableToGetLock = UnableToGetLock

    def __init__(self, app, options):
        self.app = app
        self.redis = redis.from_url(app.config['REDIS_URL'])
        self.logger = logging.getLogger(app.name + '.redis')

    def __getattr__(self, name):
        return getattr(self.redis, name)

    @contextmanager
    def lock(self, lock_key, timeout=3, nowait=False):
        conn = self.redis

        delay = 0.01 + random() / 10
        attempt = 0
        max_attempts = timeout / delay
        got_lock = None
        while not got_lock and attempt < max_attempts:
            pipe = conn.pipeline()
            pipe.setnx(lock_key, '')
            pipe.expire(lock_key, timeout)
            got_lock = pipe.execute()[0]
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
            self.logger.info('Releasing on %s', lock_key)

            try:
                conn.delete(lock_key)
            except Exception as e:
                self.logger.exception(e)


Redis = lambda **o: Container(_Redis, o, name='redis')
