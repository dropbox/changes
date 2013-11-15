from __future__ import absolute_import

import logging
import gevent
import redis

from random import random

from .container import Container


class UnableToGetLock(Exception):
    pass


class Lock(object):
    """
    Uses the defined cache backend to create a lock.

    >>> with Lock(redis, 'key name'):
    >>>     # do something
    """
    def __init__(self, conn, lock_key, timeout=3, nowait=False):
        self.conn = conn
        self.timeout = timeout
        self.lock_key = lock_key
        self.nowait = nowait

    def __enter__(self):
        lock_key = self.lock_key
        conn = self.conn
        timeout = self.timeout

        delay = 0.01 + random() / 10
        attempt = 0
        max_attempts = self.timeout / delay
        got_lock = None
        self.was_locked = False
        while not got_lock and attempt < max_attempts:
            pipe = conn.pipeline()
            pipe.setnx(lock_key, '')
            pipe.expires(lock_key, timeout)
            got_lock = pipe.execute()[0]
            if not got_lock:
                if self.nowait:
                    break
                self.was_locked = True
                gevent.sleep(delay)
                attempt += 1

        if not got_lock:
            raise UnableToGetLock('Unable to fetch lock after on %s' % (lock_key,))

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            self.conn.delete(self.lock_key)
        except Exception, e:
            logging.exception(e)


class _Redis(object):
    def __init__(self, app, options):
        self.app = app

    def __getattr__(self, name):
        return getattr(self.connection, name)

    @property
    def connection(self):
        return redis.from_url(self.app.config['REDIS_URL'])

    def lock(self, *args, **kwargs):
        return Lock(self.connection, *args, **kwargs)


Redis = lambda **o: Container(_Redis, o, name='redis')
