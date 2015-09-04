from changes.ext.redis import UnableToGetLock
from changes.config import redis
from changes.testutils import TestCase
from time import sleep


class RedisTest(TestCase):

    def test_lock_failure_doesnt_refresh(self):
        KEY = 'test_key'

        assert redis.redis.set(KEY, "initial", px=250)
        try:
            with redis.lock(KEY, nowait=True, timeout=1):
                assert False, "Shouldn't be able to acquire lock"
        except UnableToGetLock:
            pass
        # Ensure the initial set is expired, but a refresh wouldn't.
        sleep(0.3)
        assert redis.redis.get(KEY) is None
