from enum import Enum


class Status(Enum):
    unknown = 0
    queued = 1
    in_progress = 2
    finished = 3
    collecting_results = 4

    def __str__(self):
        return STATUS_LABELS[self]


class Result(Enum):
    unknown = 0
    passed = 1
    failed = 2
    skipped = 3
    errored = 4
    aborted = 5
    timedout = 6

    def __str__(self):
        return RESULT_LABELS[self]


class Provider(Enum):
    unknown = 0
    koality = 'koality'


class Cause(Enum):
    unknown = 0
    manual = 1
    push = 2
    retry = 3

    def __str__(self):
        return CAUSE_LABELS[self]

STATUS_LABELS = {
    Status.unknown: 'Unknown',
    Status.queued: 'Queued',
    Status.in_progress: 'In progress',
    Status.finished: 'Finished'
}

RESULT_LABELS = {
    Result.unknown: 'Unknown',
    Result.passed: 'Passed',
    Result.failed: 'Failed',
    Result.skipped: 'Skipped',
    Result.errored: 'Errored',
    Result.aborted: 'Aborted',
    Result.timedout: 'Timed out'
}

CAUSE_LABELS = {
    Cause.unknown: 'Unknown',
    Cause.manual: 'Manual',
    Cause.push: 'Code Push',
    Cause.retry: 'Retry',
}
