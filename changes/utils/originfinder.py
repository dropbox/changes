from __future__ import absolute_import

from collections import defaultdict

from changes.config import db
from changes.constants import Result, Status
from changes.models import Build, Job, TestCase, Source


def first(key, iterable):
    for x in iterable:
        if key(x):
            return x
    return None


def find_failure_origins(build, test_failures):
    """
    Attempt to find originating causes of failures.

    Returns a mapping of {TestCase.name_sha: Job}.
    """
    project = build.project

    if not test_failures:
        return {}

    # find any existing failures in the previous runs
    # to do this we first need to find the last passing job
    last_pass = Build.query.join(
        Source, Source.id == Build.source_id,
    ).filter(
        Build.project == project,
        Build.date_created <= build.date_created,
        Build.status == Status.finished,
        Build.result == Result.passed,
        Build.id != build.id,
        Source.patch == None,  # NOQA
    ).order_by(Build.date_created.desc()).first()

    if last_pass is None:
        return {}

    # We have to query all runs between build and last_pass. Because we're
    # paranoid about performance, we limit this to 100 results.
    previous_runs = Build.query.join(
        Source, Source.id == build.source_id,
    ).filter(
        Build.project == project,
        Build.date_created <= build.date_created,
        Build.date_created >= last_pass.date_created,
        Build.status == Status.finished,
        Build.result.in_([Result.failed, Result.passed]),
        Build.id != build.id,
        Build.id != last_pass.id,
        Source.patch == None,  # NOQA
    ).order_by(Build.date_created.desc())[:100]

    if not previous_runs:
        return {}

    # we now have a list of previous_runs so let's find all test failures in
    # these runs
    queryset = db.session.query(
        TestCase.name_sha, Job.build_id,
    ).join(
        Job, Job.id == TestCase.job_id,
    ).filter(
        Job.build_id.in_(b.id for b in previous_runs),
        Job.status == Status.finished,
        Job.result == Result.failed,
        TestCase.result == Result.failed,
        TestCase.name_sha.in_(t.name_sha for t in test_failures),
    ).group_by(
        TestCase.name_sha, Job.build_id
    )

    previous_test_failures = defaultdict(set)
    for name_sha, build_id in queryset:
        previous_test_failures[build_id].add(name_sha)

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
