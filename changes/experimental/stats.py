from changes.config import redis

PREFIX = 'CHANGES:STATS:v1:'


def incr(key):
    if redis.app:
        redis.incr(PREFIX + key)


def decr(key):
    if redis.app:
        redis.decr(PREFIX + key)


class RCount(object):
    def __init__(self, key):
        self.key = key
        pass

    def __enter__(self):
        incr(self.key)

    def __exit__(self, exc_type, exc_val, exc_tb):
        decr(self.key)
