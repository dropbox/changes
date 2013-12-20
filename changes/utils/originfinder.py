from __future__ import absolute_import

from collections import defaultdict

from changes.constants import Result, Status
from changes.models import Build, TestGroup


def first(key, iterable):
    for x in iterable:
        if key(x):
            return x
    return None


def find_failure_origins(build, test_failures):
    """
    Attempt to find originating causes of failures.

    Returns a mapping of {TestGroup.name_sha: Build}.
    """
    project = build.project

    # find any existing failures in the previous runs
    # to do this we first need to find the last passing build
    last_pass = Build.query.filter(
        Build.project == project,
        Build.date_created <= build.date_created,
        Build.status == Status.finished,
        Build.result == Result.passed,
        Build.id != build.id,
        Build.patch == None,  # NOQA
    ).order_by(Build.date_created.desc()).first()

    if last_pass is None:
        return {}

    # We have to query all runs between build and last_pass, but we only
    # care about runs where the suite failed. Because we're paranoid about
    # performance, we limit this to 100 results.
    previous_runs = Build.query.filter(
        Build.project == project,
        Build.date_created <= build.date_created,
        Build.date_created >= last_pass.date_created,
        Build.status == Status.finished,
        Build.result.in_([Result.failed, Result.passed]),
        Build.id != build.id,
        Build.id != last_pass.id,
        Build.patch == None,  # NOQA
    ).order_by(Build.date_created.desc())[:100]

    # we now have a list of previous_runs so let's find all test failures in
    # these runs
    queryset = TestGroup.query.filter(
        TestGroup.build_id.in_(b.id for b in previous_runs),
        TestGroup.result == Result.failed,
        TestGroup.num_leaves == 0,
        TestGroup.name_sha.in_(t.name_sha for t in test_failures),
    )

    previous_test_failures = defaultdict(set)
    for t in queryset:
        previous_test_failures[t.build_id].add(t.name_sha)

    failures_at_build = dict()
    searching = set(t for t in test_failures)
    last_checked_run = build

    for p_build in previous_runs:
        p_build_failures = previous_test_failures[p_build.id]
        # we have to copy the set as it might change size during iteration
        for f_test in list(searching):
            if f_test.name_sha not in p_build_failures:
                failures_at_build[f_test] = last_checked_run
                searching.remove(f_test)
        last_checked_run = p_build

    for f_test in searching:
        failures_at_build[f_test] = last_checked_run

    return failures_at_build
