import uuid

from cStringIO import StringIO

from changes.constants import Result
from changes.models import Job, TestResult
from changes.handlers.xunit import XunitHandler
from changes.testutils import SAMPLE_XUNIT


def test_result_generation():
    job = Job(
        id=uuid.uuid4(),
        project_id=uuid.uuid4()
    )

    fp = StringIO(SAMPLE_XUNIT)

    handler = XunitHandler(job)
    results = handler.get_tests(fp)

    assert len(results) == 2

    r1 = results[0]
    assert type(r1) == TestResult
    assert r1.job == job
    assert r1.package is None
    assert r1.name == 'tests.test_report'
    assert r1.duration == 0.0
    assert r1.result == Result.failed
    assert r1.message == """tests/test_report.py:1: in <module>
>   import mock
E   ImportError: No module named mock"""
    r2 = results[1]
    assert type(r2) == TestResult
    assert r2.job == job
    assert r2.package == 'tests.test_report.ParseTestResultsTest'
    assert r2.name == 'test_simple'
    assert r2.duration == 0.00165796279907
    assert r2.result == Result.passed
    assert r2.message == ''
