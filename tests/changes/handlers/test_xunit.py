import uuid

from cStringIO import StringIO

from changes.constants import Result
from changes.models.build import Build
from changes.models.test import Test
from changes.handlers.xunit import XunitHandler


UNITTEST_RESULT_XML = """
<?xml version="1.0" encoding="utf-8"?>
<testsuite errors="1" failures="0" name="" skips="0" tests="0" time="0.077">
    <testcase classname="" name="tests.test_report" time="0">
        <failure message="collection failure">tests/test_report.py:1: in &lt;module&gt;
&gt;   import mock
E   ImportError: No module named mock</failure>
    </testcase>
    <testcase classname="tests.test_report.ParseTestResultsTest" name="test_simple" time="0.00165796279907"/>
</testsuite>
""".strip()  # remove leading whitespace to prevent xml error


def test_result_generation():
    build = Build(
        id=uuid.uuid4(),
        project_id=uuid.uuid4()
    )

    fp = StringIO(UNITTEST_RESULT_XML)

    handler = XunitHandler(build)
    results = handler.get_tests(fp)

    assert len(results) == 2

    r1 = results[0]
    assert type(r1) == Test
    assert r1.build_id == build.id
    assert r1.project_id == build.project_id
    assert r1.label == 'tests.test_report'
    assert r1.duration == 0.0
    assert r1.result == Result.failed
    assert r1.message == """tests/test_report.py:1: in <module>
>   import mock
E   ImportError: No module named mock"""
    r2 = results[1]
    assert type(r2) == Test
    assert r2.build_id == build.id
    assert r2.project_id == build.project_id
    assert r2.label == 'tests.test_report.ParseTestResultsTest.test_simple'
    assert r2.duration == 0.00165796279907
    assert r2.result == Result.passed
    assert r2.message == ''
