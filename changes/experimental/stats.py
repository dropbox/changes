from changes.config import redis

PREFIX = 'CHANGES:STATS:v1:'
TRACKER_PREFIX = 'CHANGES:TRACK:'


def incr(key):
    if redis.app:
        return redis.incr(PREFIX + key)
    return 0


def decr(key):
    if redis.app:
        return redis.decr(PREFIX + key)
    return 0


def stats_get(key):
    return stats_key_get(TRACKER_PREFIX + key)


def stats_key_get(key):
    if redis.app:
        return redis.get(key)
    return ''


def stats_counter_get(key):
    return stats_key_get(PREFIX + key)


def exp_task_put(key, value):
    if redis.app:
        return redis.set(TRACKER_PREFIX + key, value)


def exp_task_delete(key):
    if redis.app:
        return redis.delete(TRACKER_PREFIX + key)


class RCount(object):
    def __init__(self, key):
        self.key = key
        pass

    def __enter__(self):
        incr(self.key)

    def __exit__(self, exc_type, exc_val, exc_tb):
        decr(self.key)
