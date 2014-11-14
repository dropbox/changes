from changes.config import redis

PREFIX = 'CHANGES:STATS:v1:'


def incr(key):
    redis.incr(PREFIX + key)


def decr(key):
    redis.decr(PREFIX + key)


class RCount(object):
    def __init__(self, key):
        self.key = key
        pass

    def __enter__(self):
        incr(self.key)

    def __exit__(self, exc_type, exc_val, exc_tb):
        decr(self.key)
