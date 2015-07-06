from base64 import b64encode

from changes.constants import Result
from changes.models import FailureReason, ItemStat
from changes.models.testresult import TestResult, TestResultManager
from changes.testutils.cases import TestCase


def _stat(jobstep, name):
    id = jobstep.id
    return ItemStat.query.filter_by(name=name, item_id=id)[0].value


class TestResultManagerTestCase(TestCase):
    def test_simple(self):
        from changes.models import TestCase

        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)

        results = [
            TestResult(
                step=jobstep,
                name='test_bar',
                package='tests.changes.handlers.test_xunit',
                result=Result.failed,
                message='collection failed',
                duration=156,
                artifacts=[{
                    'name': 'artifact_name',
                    'type': 'text',
                    'base64': b64encode('sample content')}]),
            TestResult(
                step=jobstep,
                name='test_foo',
                package='tests.changes.handlers.test_coverage',
                result=Result.passed,
                message='foobar passed',
                duration=12,
                reruns=1,
            ),
        ]
        manager = TestResultManager(jobstep)
        manager.save(results)

        testcase_list = sorted(TestCase.query.all(), key=lambda x: x.name)

        assert len(testcase_list) == 2

        for test in testcase_list:
            assert test.job_id == job.id
            assert test.step_id == jobstep.id
            assert test.project_id == project.id

        assert testcase_list[0].name == 'tests.changes.handlers.test_coverage.test_foo'
        assert testcase_list[0].result == Result.passed
        assert testcase_list[0].message == 'foobar passed'
        assert testcase_list[0].duration == 12
        assert testcase_list[0].reruns == 1

        assert testcase_list[1].name == 'tests.changes.handlers.test_xunit.test_bar'
        assert testcase_list[1].result == Result.failed
        assert testcase_list[1].message == 'collection failed'
        assert testcase_list[1].duration == 156
        assert testcase_list[1].reruns is 0

        testartifacts = testcase_list[1].artifacts
        assert len(testartifacts) == 1
        assert testartifacts[0].file.get_file().read() == 'sample content'

        assert _stat(jobstep, 'test_count') == 2
        assert _stat(jobstep, 'test_failures') == 1
        assert _stat(jobstep, 'test_duration') == 168
        assert _stat(jobstep, 'test_rerun_count') == 1

        failures = FailureReason.query.filter_by(step_id=jobstep.id).all()
        assert failures == []

    def test_duplicate_tests_in_same_result_list(self):
        from changes.models import TestCase

        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase, label='STEP1')

        results = [
            TestResult(
                step=jobstep,
                name='test_foo',
                package='project.tests',
                result=Result.passed,
                duration=12,
                reruns=0,
                artifacts=[{
                    'name': 'artifact_name',
                    'type': 'text',
                    'base64': b64encode('first artifact')}]
            ),
            TestResult(
                step=jobstep,
                name='test_bar',
                package='project.tests',
                result=Result.passed,
                duration=13,
                reruns=0,
            ),
            TestResult(
                step=jobstep,
                name='test_foo',
                package='project.tests',
                result=Result.passed,
                duration=11,
                reruns=0,
                artifacts=[{
                    'name': 'artifact_name',
                    'type': 'text',
                    'base64': b64encode('second artifact')}]
            ),
        ]
        manager = TestResultManager(jobstep)
        manager.save(results)

        testcase_list = sorted(TestCase.query.all(), key=lambda x: x.name)

        assert len(testcase_list) == 2

        for test in testcase_list:
            assert test.job_id == job.id
            assert test.step_id == jobstep.id
            assert test.project_id == project.id

        assert testcase_list[0].name == 'project.tests.test_bar'
        assert testcase_list[0].result == Result.passed
        assert testcase_list[0].message is None
        assert testcase_list[0].duration == 13
        assert testcase_list[0].reruns == 0
        assert len(testcase_list[0].artifacts) == 0

        assert testcase_list[1].name == 'project.tests.test_foo'
        assert testcase_list[1].result == Result.failed
        assert testcase_list[1].message == 'Duplicate test in step STEP1'
        assert testcase_list[1].duration == 12
        assert testcase_list[1].reruns == 0

        testartifacts = testcase_list[1].artifacts
        assert len(testartifacts) == 2
        a1 = testartifacts[0].file.get_file().read()
        a2 = testartifacts[1].file.get_file().read()
        assert {a1, a2} == {'first artifact', 'second artifact'}

        assert _stat(jobstep, 'test_count') == 2
        assert _stat(jobstep, 'test_failures') == 1
        assert _stat(jobstep, 'test_duration') == 25
        assert _stat(jobstep, 'test_rerun_count') == 0

        failures = FailureReason.query.filter_by(step_id=jobstep.id).all()
        assert len(failures) == 1
        assert failures[0].reason == 'duplicate_test_name'

    def test_duplicate_tests_in_different_result_lists(self):
        from changes.models import TestCase

        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase, label='STEP1')

        results = [
            TestResult(
                step=jobstep,
                name='test_foo',
                package='project.tests',
                result=Result.passed,
                duration=12,
                reruns=0,
                artifacts=[{
                    'name': 'one_artifact',
                    'type': 'text',
                    'base64': b64encode('first artifact')}]
            ),
            TestResult(
                step=jobstep,
                name='test_bar',
                package='project.tests',
                result=Result.passed,
                duration=13,
                reruns=0,
            ),
        ]
        manager = TestResultManager(jobstep)
        manager.save(results)

        testcase_list = sorted(TestCase.query.all(), key=lambda x: x.name)

        assert len(testcase_list) == 2

        for test in testcase_list:
            assert test.job_id == job.id
            assert test.step_id == jobstep.id
            assert test.project_id == project.id

        assert testcase_list[0].name == 'project.tests.test_bar'
        assert testcase_list[0].result == Result.passed
        assert testcase_list[0].message is None
        assert testcase_list[0].duration == 13
        assert testcase_list[0].reruns == 0
        assert len(testcase_list[0].artifacts) == 0

        assert testcase_list[1].name == 'project.tests.test_foo'
        assert testcase_list[1].result == Result.passed
        assert testcase_list[1].message is None
        assert testcase_list[1].duration == 12
        assert testcase_list[1].reruns == 0

        testartifacts = testcase_list[1].artifacts
        assert len(testartifacts) == 1
        a1 = testartifacts[0].file.get_file().read()
        assert a1 == 'first artifact'

        assert _stat(jobstep, 'test_count') == 2
        assert _stat(jobstep, 'test_failures') == 0
        assert _stat(jobstep, 'test_duration') == 25
        assert _stat(jobstep, 'test_rerun_count') == 0

        jobstep2 = self.create_jobstep(jobphase, label='STEP2')

        results = [
            TestResult(
                step=jobstep2,
                name='test_foo',
                package='project.tests',
                result=Result.passed,
                duration=11,
                reruns=0,
                artifacts=[{
                    'name': 'another_artifact',
                    'type': 'text',
                    'base64': b64encode('second artifact')}]
            ),
            TestResult(
                step=jobstep2,
                name='test_baz',
                package='project.tests',
                result=Result.passed,
                duration=18,
                reruns=2,
            ),
        ]
        manager = TestResultManager(jobstep2)
        manager.save(results)

        testcase_list = sorted(TestCase.query.all(), key=lambda x: x.name)

        assert len(testcase_list) == 3

        for test in testcase_list:
            assert test.job_id == job.id
            assert test.project_id == project.id

        assert testcase_list[0].step_id == jobstep.id
        assert testcase_list[0].name == 'project.tests.test_bar'
        assert testcase_list[0].result == Result.passed
        assert testcase_list[0].message is None
        assert testcase_list[0].duration == 13
        assert testcase_list[0].reruns == 0

        assert testcase_list[1].step_id == jobstep2.id
        assert testcase_list[1].name == 'project.tests.test_baz'
        assert testcase_list[1].result == Result.passed
        assert testcase_list[1].message is None
        assert testcase_list[1].duration == 18
        assert testcase_list[1].reruns == 2

        assert testcase_list[2].step_id == jobstep.id
        assert testcase_list[2].name == 'project.tests.test_foo'
        assert testcase_list[2].result == Result.failed
        assert testcase_list[2].message == (
            'Duplicate test in step STEP1 and STEP2')
        assert testcase_list[2].duration == 12
        assert testcase_list[2].reruns == 0

        testartifacts = testcase_list[2].artifacts
        assert len(testartifacts) == 2
        a1 = testartifacts[0].file.get_file().read()
        a2 = testartifacts[1].file.get_file().read()
        assert {a1, a2} == {'first artifact', 'second artifact'}

        # Stats for original step are unharmed:

        assert _stat(jobstep, 'test_count') == 2
        assert _stat(jobstep, 'test_failures') == 1
        assert _stat(jobstep, 'test_duration') == 25
        assert _stat(jobstep, 'test_rerun_count') == 0

        # Stats for new step:

        assert _stat(jobstep2, 'test_count') == 1
        assert _stat(jobstep2, 'test_failures') == 0
        assert _stat(jobstep2, 'test_duration') == 18
        assert _stat(jobstep2, 'test_rerun_count') == 1

        failures = FailureReason.query.filter_by(step_id=jobstep.id).all()
        assert len(failures) == 0

        failures = FailureReason.query.filter_by(step_id=jobstep2.id).all()
        assert len(failures) == 1
        assert failures[0].reason == 'duplicate_test_name'
