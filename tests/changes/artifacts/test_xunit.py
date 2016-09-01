import logging
import mock
import os
import pytest
import time
import uuid

from cStringIO import StringIO

from changes.artifacts.xunit import XunitHandler, truncate_message, _TRUNCATION_HEADER
from changes.constants import Result
from changes.models.failurereason import FailureReason
from changes.models.jobstep import JobStep
from changes.models.testresult import TestResult
from changes.testutils import (
    SAMPLE_XUNIT, SAMPLE_XUNIT_DOUBLE_CASES, SAMPLE_XUNIT_MULTIPLE_SUITES,
    SAMPLE_XUNIT_MULTIPLE_EMPTY_PASSED, SAMPLE_XUNIT_MULTIPLE_EMPTY_FAILED_FAILURE,
    SAMPLE_XUNIT_MULTIPLE_EMPTY_FAILED_ERROR,
)
from changes.testutils.cases import TestCase


@pytest.mark.parametrize('xml, suite_name, duration', [
    (SAMPLE_XUNIT, "", 77),
    (SAMPLE_XUNIT_DOUBLE_CASES, "pytest", 19),
])
def test_get_test_single_suite(xml, suite_name, duration):
    jobstep = JobStep(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
    )

    fp = StringIO(xml)

    handler = XunitHandler(jobstep)
    suites = handler.get_test_suites(fp)
    assert len(suites) == 1
    assert suites[0].name == suite_name
    assert suites[0].duration == duration
    assert suites[0].result == Result.failed

    # test the equivalence of get_tests and get_test_suites in the case where
    # there is only one test suite, so that we can call get_tests directly
    # in the rest of this file.
    fp.seek(0)
    other_results = handler.get_tests(fp)

    results = suites[0].test_results
    assert len(results) == len(other_results)
    for i in range(len(results)):
        assert other_results[i].step == results[i].step
        assert other_results[i].step == results[i].step
        assert other_results[i]._name == results[i]._name
        assert other_results[i]._package == results[i]._package
        assert other_results[i].message == results[i].message
        assert other_results[i].result is results[i].result
        assert other_results[i].duration == results[i].duration
        assert other_results[i].reruns == results[i].reruns
        assert other_results[i].artifacts == results[i].artifacts
        assert other_results[i].owner == results[i].owner
        assert other_results[i].message_offsets == results[i].message_offsets


def test_get_test_suite_multiple():
    jobstep = JobStep(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
    )
    # needed for logging when a test suite has no duration
    jobstep.job = mock.MagicMock()

    fp = StringIO(SAMPLE_XUNIT_MULTIPLE_SUITES)

    handler = XunitHandler(jobstep)
    suites = handler.get_test_suites(fp)
    assert len(suites) == 3
    assert suites[0].name is None
    assert suites[0].duration is None
    assert suites[0].result == Result.failed
    assert len(suites[0].test_results) == 3

    assert suites[1].name == 'suite2'
    assert suites[1].duration == 77
    assert suites[1].result == Result.failed
    assert len(suites[1].test_results) == 3

    assert suites[2].name == ''
    assert suites[2].duration is None
    assert suites[2].result == Result.failed
    assert len(suites[2].test_results) == 3

    tests = handler.aggregate_tests_from_suites(suites)
    assert len(tests) == 7  # 10 test cases, 3 of which are duplicates


@pytest.mark.parametrize('xml,result', [
    (SAMPLE_XUNIT_MULTIPLE_EMPTY_PASSED, Result.passed),
    (SAMPLE_XUNIT_MULTIPLE_EMPTY_FAILED_FAILURE, Result.failed),
    (SAMPLE_XUNIT_MULTIPLE_EMPTY_FAILED_ERROR, Result.failed),
])
def test_get_test_suite_multiple_empty(xml, result):
    jobstep = JobStep(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
    )
    # needed for logging when a test suite has no duration
    jobstep.job = mock.MagicMock()

    fp = StringIO(xml)

    handler = XunitHandler(jobstep)
    suites = handler.get_test_suites(fp)
    assert len(suites) == 2
    assert suites[0].name == 'suite-name'
    assert suites[0].duration is None
    assert suites[0].result is result
    assert len(suites[0].test_results) == 0

    assert suites[1].name == 'null'
    assert suites[1].duration is None
    assert suites[1].result == Result.passed
    assert len(suites[1].test_results) == 1


def test_result_generation():
    jobstep = JobStep(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
    )

    fp = StringIO(SAMPLE_XUNIT)

    handler = XunitHandler(jobstep)
    results = handler.get_tests(fp)

    assert len(results) == 3

    r1 = results[0]
    assert type(r1) == TestResult
    assert r1.step == jobstep
    assert r1.package is None
    assert r1.name == 'tests.test_report'
    assert r1.duration == 0.0
    assert r1.result == Result.failed
    assert r1.message is None
    assert len(r1.message_offsets) == 1
    label, start, length = r1.message_offsets[0]
    assert label == 'failure'
    assert SAMPLE_XUNIT[start:start + length] == """\
tests/test_report.py:1: in &lt;module&gt;
&gt;   import mock
E   ImportError: No module named mock"""
    assert r1.owner == 'foo'
    r2 = results[1]
    assert type(r2) == TestResult
    assert r2.step == jobstep
    assert r2.package is None
    assert r2.name == 'tests.test_report.ParseTestResultsTest.test_simple'
    assert r2.duration == 1.65796279907
    assert r2.result == Result.passed
    assert r2.message is None
    assert r2.message_offsets == []
    assert r2.reruns == 1
    assert r2.owner is None
    r3 = results[2]
    assert type(r3) == TestResult
    assert r3.step == jobstep
    assert r3.package is None
    assert r3.name == 'test_simple.SampleTest.test_falsehood'
    assert r3.duration == 500.0
    assert r3.result == Result.passed
    assert r3.message is None
    assert len(r3.message_offsets) == 3
    label, start, length = r3.message_offsets[0]
    assert label == 'system-out'
    assert SAMPLE_XUNIT[start:start + length] == 'Running SampleTest'
    label, start, length = r3.message_offsets[1]
    assert label == 'error'
    assert SAMPLE_XUNIT[start:start + length] == """\
test_simple.py:4: in tearDown
    1/0
E   ZeroDivisionError: integer division or modulo by zero"""
    label, start, length = r3.message_offsets[2]
    assert label == 'system-out'
    assert SAMPLE_XUNIT[start:start + length] == 'Running SampleTest'
    assert r3.reruns == 3
    assert r3.owner is None


def test_bad_encoding():
    jobstep = JobStep(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
    )

    fp = StringIO(SAMPLE_XUNIT.replace('"utf-8"', '"utf8"'))

    handler = XunitHandler(jobstep)
    results = handler.get_tests(fp)

    assert len(results) == 3


def test_result_generation_when_one_test_has_two_cases():
    jobstep = JobStep(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
    )

    fp = StringIO(SAMPLE_XUNIT_DOUBLE_CASES)

    handler = XunitHandler(jobstep)
    results = handler.get_tests(fp)

    assert len(results) == 2

    r1 = results[0]
    assert type(r1) is TestResult
    assert r1.step == jobstep
    assert r1.package is None
    assert r1.name == 'test_simple.SampleTest.test_falsehood'
    assert r1.duration == 750.0
    assert r1.result == Result.failed
    assert r1.message == ''
    assert len(r1.message_offsets) == 2
    label, start, length = r1.message_offsets[0]
    assert label == 'failure'
    assert SAMPLE_XUNIT_DOUBLE_CASES[start:start + length] == """\
test_simple.py:8: in test_falsehood
    assert False
E   AssertionError: assert False"""
    label, start, length = r1.message_offsets[1]
    assert label == 'error'
    assert SAMPLE_XUNIT_DOUBLE_CASES[start:start + length] == """\
test_simple.py:4: in tearDown
    1/0
E   ZeroDivisionError: integer division or modulo by zero"""
    assert r1.reruns == 3

    r2 = results[1]
    assert type(r2) is TestResult
    assert r2.step == jobstep
    assert r2.package is None
    assert r2.name == 'test_simple.SampleTest.test_truth'
    assert r2.duration == 1250.0
    assert r2.result == Result.failed
    assert r2.message is None
    assert len(r2.message_offsets) == 1
    label, start, length = r2.message_offsets[0]
    assert label == 'failure'
    assert SAMPLE_XUNIT_DOUBLE_CASES[start:start + length] == """\
test_simple.py:4: in tearDown
    1/0
E   ZeroDivisionError: integer division or modulo by zero"""
    assert r2.reruns == 0


def test_result_generation_when_a_quarantined_test_has_two_cases():
    jobstep = JobStep(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
    )

    XUNIT_STRING = (SAMPLE_XUNIT_DOUBLE_CASES
                    .replace('<testcase c', '<testcase quarantined="1" c', 1)
                    .replace('<testcase c', '<testcase quarantined="1" c', 1))
    fp = StringIO(XUNIT_STRING)

    handler = XunitHandler(jobstep)
    results = handler.get_tests(fp)

    assert len(results) == 2

    r1 = results[0]
    assert type(r1) is TestResult
    assert r1.step == jobstep
    assert r1.package is None
    assert r1.name == 'test_simple.SampleTest.test_falsehood'
    assert r1.duration == 750.0
    assert r1.result == Result.quarantined_failed
    assert r1.message == ''
    assert len(r1.message_offsets) == 2
    label, start, length = r1.message_offsets[0]
    assert label == 'failure'
    assert XUNIT_STRING[start:start + length] == """\
test_simple.py:8: in test_falsehood
    assert False
E   AssertionError: assert False"""
    label, start, length = r1.message_offsets[1]
    assert label == 'error'
    assert XUNIT_STRING[start:start + length] == """\
test_simple.py:4: in tearDown
    1/0
E   ZeroDivisionError: integer division or modulo by zero"""
    assert r1.reruns == 3

    r2 = results[1]
    assert type(r2) is TestResult
    assert r2.step == jobstep
    assert r2.package is None
    assert r2.name == 'test_simple.SampleTest.test_truth'
    assert r2.duration == 1250.0
    assert r2.result == Result.failed
    assert r2.message is None
    assert len(r2.message_offsets) == 1
    label, start, length = r2.message_offsets[0]
    assert label == 'failure'
    assert XUNIT_STRING[start:start + length] == """\
test_simple.py:4: in tearDown
    1/0
E   ZeroDivisionError: integer division or modulo by zero"""
    assert r2.reruns == 0


def test_truncate_message():
    suffix = "But it'll be truncated anyway."
    original = ("This isn't really that big.\n" * 1024) + suffix
    limit = len(suffix) + 3
    newmsg = truncate_message(original, limit=len(suffix) + 3)
    assert len(newmsg) < limit + len(_TRUNCATION_HEADER)

    short = "Hello"
    assert short == truncate_message(short, limit=1024)

    single_long_line = "Text " * 1024
    assert truncate_message(single_long_line, limit=1024) == _TRUNCATION_HEADER

    # Because this was previously broken.
    assert truncate_message(None, limit=1024) is None


class BadArtifactTestCase(TestCase):
    def test_invalid_junit(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)
        artifact = self.create_artifact(jobstep, 'junit.xml')

        missing_name = """<?xml version="1.0" encoding="utf-8"?>
        <testsuite errors="1" failures="0" name="" skips="0" tests="0" time="0.077">
            <testcase classname="" time="0" owner="foo">
                <failure message="collection failure">tests/test_report.py:1: in &lt;module&gt;
        &gt;   import mock
        E   ImportError: No module named mock</failure>
            </testcase>
            <testcase classname="tests.test_report.ParseTestResultsTest" name="test_simple" time="0.001607" rerun="1"/>
        </testsuite>"""
        fp = StringIO(missing_name)

        handler = XunitHandler(jobstep)
        results = handler.process(fp, artifact)
        assert results == []
        reason = FailureReason.query.filter(
            FailureReason.step_id == jobstep.id
        ).first()
        assert reason is not None


class TestFromFileTestCase(TestCase):
    def test_from_file(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)
        logger = logging.getLogger('xunit')

        path = os.path.join(os.path.dirname(__file__), 'fixtures', 'junit.xml.test')

        with open(path, 'rb') as fp:
            contents = fp.read()

        start = time.clock()
        handler = XunitHandler(jobstep)
        results = handler.get_tests(StringIO(contents))
        logger.info("XUnit handler ran in %f seconds." % (time.clock() - start))

        assert len(results) == 675
        assert results[0].name == 'tests.changes.api.test_build_details.TestCase'
        assert results[0].result == Result.skipped
        assert results[674].name == 'tests.changes.web.test_auth.LogoutViewTest.test_simple'
        assert results[674].result == Result.passed
