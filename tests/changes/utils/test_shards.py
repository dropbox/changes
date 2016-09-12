from changes.utils.shards import shard
from changes.testutils.cases import TestCase


class ShardingTestCase(TestCase):
    def test_shard(self):
        tests = [
            'foo/bar',
            'foo/baz',
            'foo/bar/test_biz',
            'foo/bar/test_buz',
        ]
        test_weights = {
            ('foo', 'bar'): 50,
            ('foo', 'baz'): 15,
            ('foo', 'bar', 'test_biz'): 10,
            ('foo', 'bar', 'test_buz'): 200,
        }
        avg_test_time = sum(test_weights.values()) / len(test_weights)

        groups = shard(tests, 2, test_weights, avg_test_time, normalize_object_name=lambda x: tuple(x.split('/')))
        assert len(groups) == 2
        groups.sort()
        assert groups[0] == (78, ['foo/bar', 'foo/baz', 'foo/bar/test_biz'])
        assert groups[1] == (201, ['foo/bar/test_buz'])

        groups = shard(tests, 3, test_weights, avg_test_time, normalize_object_name=lambda x: tuple(x.split('/')))
        assert len(groups) == 3
        groups.sort()
        assert groups[0] == (27, ['foo/baz', 'foo/bar/test_biz'])
        assert groups[1] == (51, ['foo/bar'])
        assert groups[2] == (201, ['foo/bar/test_buz'])

        # more shards than tests
        groups = shard(tests, len(tests) * 2, test_weights, avg_test_time, normalize_object_name=lambda x: tuple(x.split('/')))
        assert len(groups) == len(tests)
