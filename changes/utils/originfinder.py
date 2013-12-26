from __future__ import absolute_import

from collections import defaultdict

from changes.constants import Result, Status
from changes.models import Job, TestGroup


def first(key, iterable):
    for x in iterable:
        if key(x):
            return x
    return None


def find_failure_origins(job, test_failures):
    """
    Attempt to find originating causes of failures.

    Returns a mapping of {TestGroup.name_sha: Job}.
    """
    project = job.project

    # find any existing failures in the previous runs
    # to do this we first need to find the last passing job
    last_pass = Job.query.filter(
        Job.project == project,
        Job.date_created <= job.date_created,
        Job.status == Status.finished,
        Job.result == Result.passed,
        Job.id != job.id,
        Job.patch == None,  # NOQA
    ).order_by(Job.date_created.desc()).first()

    if last_pass is None:
        return {}

    # We have to query all runs between job and last_pass, but we only
    # care about runs where the suite failed. Because we're paranoid about
    # performance, we limit this to 100 results.
    previous_runs = Job.query.filter(
        Job.project == project,
        Job.date_created <= job.date_created,
        Job.date_created >= last_pass.date_created,
        Job.status == Status.finished,
        Job.result.in_([Result.failed, Result.passed]),
        Job.id != job.id,
        Job.id != last_pass.id,
        Job.patch == None,  # NOQA
    ).order_by(Job.date_created.desc())[:100]

    # we now have a list of previous_runs so let's find all test failures in
    # these runs
    queryset = TestGroup.query.filter(
        TestGroup.job_id.in_(b.id for b in previous_runs),
        TestGroup.result == Result.failed,
        TestGroup.num_leaves == 0,
        TestGroup.name_sha.in_(t.name_sha for t in test_failures),
    )

    previous_test_failures = defaultdict(set)
    for t in queryset:
        previous_test_failures[t.job_id].add(t.name_sha)

    failures_at_job = dict()
    searching = set(t for t in test_failures)
    last_checked_run = job

    for p_job in previous_runs:
        p_job_failures = previous_test_failures[p_job.id]
        # we have to copy the set as it might change size during iteration
        for f_test in list(searching):
            if f_test.name_sha not in p_job_failures:
                failures_at_job[f_test] = last_checked_run
                searching.remove(f_test)
        last_checked_run = p_job

    for f_test in searching:
        failures_at_job[f_test] = last_checked_run

    return failures_at_job
