import os
from enum import Enum

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

NUM_PREVIOUS_RUNS = 50

# Default custom css file that's searched for in the webapp/custom/ directory
# if not specified in changes.conf.py
CUSTOM_CSS_FILE = "changes.less"


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


class Result(Enum):
    unknown = 0
    # 'aborted' indicates intentional cancellation or an unrecoverable error.
    #
    # Operations that time out are not considered aborted, even though the timeout
    # may result in intentional cancellation or be the result of an infrastructural failure.
    # This is because we don't usually know the cause of timeouts, so we assume build failure to
    # be safe.
    aborted = 5
    passed = 1
    skipped = 3
    failed = 2
    # 'infra_failed' indicates that a build encountered a problem in Changes or
    # backends and has no meaningful result. Not all builds which fail for
    # infrastructural reasons will be reported as 'infra_failed', but we should
    # do our best to identify internal failures and use this Result.
    infra_failed = 6
    # these indicate results for tests that are quarantined
    quarantined_passed = 11
    quarantined_failed = 12
    quarantined_skipped = 13

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
    Status.collecting_results: 'Collecting Results',
    Status.finished: 'Finished',
    Status.allocated: 'Allocated',
    Status.pending_allocation: 'Queued',
}

STATUS_PRIORITY = (
    Status.in_progress,
    Status.queued,
    Status.allocated,
    Status.pending_allocation,
    Status.collecting_results,
    Status.finished,
)

RESULT_LABELS = {
    Result.unknown: 'Unknown',
    Result.passed: 'Passed',
    Result.failed: 'Failed',
    Result.skipped: 'Skipped',
    Result.aborted: 'Aborted',
    Result.infra_failed: 'Infrastructure failed',
    Result.quarantined_passed: 'Passed (quarantine)',
    Result.quarantined_failed: 'Failed (quarantine)',
    Result.quarantined_skipped: 'Skipped (quarantine)',
}

RESULT_PRIORITY = (
    Result.aborted,
    Result.failed,
    Result.infra_failed,
    Result.unknown,
    Result.passed,
    Result.skipped,
    Result.quarantined_passed,
    Result.quarantined_failed,
    Result.quarantined_skipped,
)

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
    'changes.backends.jenkins.buildstep.JenkinsGenericBuildStep',
    'changes.backends.jenkins.buildsteps.test_collector.JenkinsTestCollectorBuildStep',
)
