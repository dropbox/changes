from changes.ext.redis import UnableToGetLock
from changes.config import redis
from changes.testutils import TestCase
from time import sleep


class RedisTest(TestCase):

    def test_lock_blocking(self):
        KEY = 'test_key'
        with redis.lock(KEY, expire=0.3, nowait=True):
            try:
                with redis.lock(KEY, blocking_timeout=0.2):
                    assert False, "Shouldn't be able to acquire lock"
            except UnableToGetLock:
                pass
            # should succeed, rather than throwing UnableToGetLock
            with redis.lock(KEY, blocking_timeout=0.2):
                pass

    def test_lock_cant_unlock_others(self):
        KEY = 'test_key'
        initial_lock = redis.lock(KEY, expire=0.2, nowait=True)
        initial_lock.__enter__()
        # expire the current lock
        sleep(0.3)

        lock2 = redis.lock(KEY, nowait=True)
        lock2.__enter__()

        initial_lock.__exit__(None, None, None)

        # ensure that didn't unlock lock2
        try:
            with redis.lock(KEY, nowait=True):
                assert False, "Shouldn't be able to acquire lock"
        except UnableToGetLock:
            pass
        finally:
            lock2.__exit__(None, None, None)
