import os
from enum import Enum

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

NUM_PREVIOUS_RUNS = 50


class OrderedEnum(Enum):
    def get_order(self):
        return sorted(self.__members__, key=lambda x: x._value_)

    def __ge__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        order = self.get_order()
        return order.index(self) >= order.index(other)

    def __gt__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        order = self.get_order()
        return order.index(self) > order.index(other)

    def __le__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        order = self.get_order()
        return order.index(self) <= order.index(other)

    def __lt__(self, other):
        if type(self) is not type(other):
            return NotImplemented
        order = self.get_order()
        return order.index(self) < order.index(other)


class Status(Enum):
    unknown = 0
    queued = 1
    in_progress = 2
    finished = 3
    collecting_results = 4
    allocated = 5
    pending_allocation = 6

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

    def get_order(self):
        return [
            Result.skipped,
            Result.passed,
            Result.unknown,
            Result.failed,
            Result.aborted,
        ]


class Provider(Enum):
    unknown = 0
    koality = 'koality'


class Cause(Enum):
    unknown = 0
    manual = 1
    push = 2
    retry = 3
    snapshot = 4

    def __str__(self):
        return CAUSE_LABELS[self]


class ProjectStatus(Enum):
    unknown = 0
    active = 1
    inactive = 2

    def __str__(self):
        return PROJECT_STATUS_LABELS[self]


PROJECT_STATUS_LABELS = {
    ProjectStatus.unknown: 'Unknown',
    ProjectStatus.active: 'Active',
    ProjectStatus.inactive: 'Inactive',
}

STATUS_LABELS = {
    Status.unknown: 'Unknown',
    Status.queued: 'Queued',
    Status.in_progress: 'In progress',
    Status.finished: 'Finished',
    Status.allocated: 'Allocated',
    Status.pending_allocation: 'Queued',
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
    Cause.snapshot: 'Snapshot',
}

IMPLEMENTATION_CHOICES = (
    'changes.buildsteps.dummy.DummyBuildStep',
    'changes.buildsteps.default.DefaultBuildStep',
    'changes.buildsteps.lxc.LXCBuildStep',
    'changes.backends.jenkins.buildstep.JenkinsBuildStep',
    'changes.backends.jenkins.buildstep.JenkinsFactoryBuildStep',
    'changes.backends.jenkins.buildstep.JenkinsGenericBuildStep',
    'changes.backends.jenkins.buildsteps.collector.JenkinsCollectorBuildStep',
    'changes.backends.jenkins.buildsteps.test_collector.JenkinsTestCollectorBuildStep',
)
