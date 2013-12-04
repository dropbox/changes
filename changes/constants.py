import os
from enum import Enum

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

NUM_PREVIOUS_RUNS = 50


class OrderedEnum(Enum):
    def __ge__(self, other):
        if type(self) is type(other):
            return self._value_ >= other._value_
        return NotImplemented

    def __gt__(self, other):
        if type(self) is type(other):
            return self._value_ > other._value_
        return NotImplemented

    def __le__(self, other):
        if type(self) is type(other):
            return self._value_ <= other._value_
        return NotImplemented

    def __lt__(self, other):
        if type(self) is type(other):
            return self._value_ < other._value_
        return NotImplemented


class Status(Enum):
    unknown = 0
    queued = 1
    in_progress = 2
    finished = 3
    collecting_results = 4

    def __str__(self):
        return STATUS_LABELS[self]


class Result(OrderedEnum):
    unknown = 0
    aborted = 5
    passed = 1
    skipped = 3
    failed = 2

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
    Result.aborted: 'Aborted',
}

CAUSE_LABELS = {
    Cause.unknown: 'Unknown',
    Cause.manual: 'Manual',
    Cause.push: 'Code Push',
    Cause.retry: 'Retry',
}
