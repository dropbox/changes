import sys

from changes.constants import (
    Result, RESULT_PRIORITY,
    SelectiveTestingPolicy, SELECTIVE_TESTING_POLICY_PRIORITY,
    Status, STATUS_PRIORITY,
)


def safe_agg(func, sequence, default=None):
    m = None
    for item in sequence:
        if item is None:
            continue
        elif m is None:
            m = item
        else:
            m = func(m, item)
    if m is None:
        m = default
    return m


def _aggregate_constant(item_list, priority_list, default):
    value = default
    priority = sys.maxint
    for item_value in item_list:
        if item_value == default:
            continue

        idx = priority_list.index(item_value)
        if idx < priority:
            value = item_value
            priority = idx

    return value


def _aggregate_constant_result(item_list, priority_list, default):
    value = default
    priority = sys.maxint
    for item_value in item_list:
        idx = priority_list.index(item_value)
        if idx < priority:
            value = item_value
            priority = idx

    return value


def aggregate_status(status_list):
    return _aggregate_constant(status_list, STATUS_PRIORITY, Status.unknown)


def aggregate_result(result_list):
    return _aggregate_constant_result(result_list, RESULT_PRIORITY, Result.unknown)


def aggregate_selective_testing_policy(policy_list):
    return _aggregate_constant_result(policy_list, SELECTIVE_TESTING_POLICY_PRIORITY, SelectiveTestingPolicy.disabled)
