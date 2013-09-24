from enum import Enum


class Status(Enum):
    unknown = 0
    queued = 1
    inprogress = 2
    finished = 3

    def __str__(self):
        return STATUS_LABELS[self]


class Result(Enum):
    unknown = 0
    passed = 1
    failed = 2
    skipped = 3
    errored = 4

    def __str__(self):
        return RESULT_LABELS[self]


class Provider(Enum):
    unknown = 0
    koality = 'koality'


STATUS_LABELS = {
    Status.unknown: 'unknown',
    Status.queued: 'queued',
    Status.inprogress: 'in progress',
    Status.finished: 'finished'
}

RESULT_LABELS = {
    Result.unknown: 'unknown',
    Result.passed: 'passed',
    Result.failed: 'failed',
}
