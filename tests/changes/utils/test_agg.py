from changes.constants import Result, Status
from changes.utils.agg import aggregate_result, aggregate_status


def test_aggregate_result():
    status_list = [Result.passed, Result.failed, Result.unknown]
    assert aggregate_result(status_list) == Result.failed

    status_list = [Result.passed, Result.unknown]
    assert aggregate_result(status_list) == Result.unknown

    status_list = [Result.passed, Result.skipped]
    assert aggregate_result(status_list) == Result.passed


def test_aggregate_status():
    status_list = [Status.finished, Status.queued, Status.in_progress, Status.unknown]
    assert aggregate_status(status_list) == Status.in_progress

    status_list = [Status.finished, Status.queued, Status.unknown]
    assert aggregate_status(status_list) == Status.queued

    status_list = [Status.finished, Status.unknown]
    assert aggregate_status(status_list) == Status.finished
