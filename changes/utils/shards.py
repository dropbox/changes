import heapq

from flask import current_app
from typing import Any, Callable, cast, Dict, List, Tuple, TypeVar  # NOQA


Normalized = TypeVar('Normalized')


def shard(objects, max_shards, object_stats, avg_time, normalize_object_name=cast(Callable[[str], Normalized], lambda x: x)):
    # type: (List[str], int, Dict[Normalized, int], int, Callable[[str], Normalized]) -> List[Tuple[int, List[str]]]
    """
    Breaks a set of objects into shards.

    Args:
        objects (list): A list of object names.
        max_shards (int): Maximum amount of shards over which to distribute the objects.
        test_stats (dict): A mapping from normalized object name to duration.
        avg_test_time (int): Average duration of a single object.
        normalize_object_name (str -> Tuple[str, ...]): a function that normalizes object names.
            This function can return anything, as long as it is consistent with `test_stats`.

    Returns:
        list: Shards. Each element is a pair containing the weight for that
            shard and the object names assigned to that shard.
    """
    def get_object_duration(test_name):
        # type: (str) -> int
        normalized = normalize_object_name(test_name)
        result = object_stats.get(normalized)
        if result is None:
            if object_stats:
                current_app.logger.info('No existing duration found for test %r', test_name)
            result = avg_time
        return result

    # don't use more shards than there are objects
    num_shards = min(len(objects), max_shards)
    # Each element is a pair (weight, objects).
    groups = [(0, []) for _ in range(num_shards)]  # type: List[Tuple[int, List[str]]]
    # Groups is already a proper heap, but we'll call this to guarantee it.
    heapq.heapify(groups)
    weighted_tests = [(get_object_duration(t), t) for t in objects]
    for weight, test in sorted(weighted_tests, reverse=True):
        group_weight, group_tests = heapq.heappop(groups)
        group_weight += 1 + weight
        group_tests.append(test)
        heapq.heappush(groups, (group_weight, group_tests))

    return groups
