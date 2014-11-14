from changes.config import redis

PREFIX = 'CHANGES:STATS:'


def incr(key):
    redis.incr(PREFIX + key)


def decr(key):
    redis.decr(PREFIX + key)
