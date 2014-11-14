from changes.config import redis

PREFIX = 'changes:stats:'


def incr(key):
    redis.incr(PREFIX + key)


def decr(key):
    redis.decr(PREFIX + key)
