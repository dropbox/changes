from base64 import b64encode

from changes.constants import Result
from changes.models import ItemStat
from changes.models.testresult import TestResult, TestResultManager
from changes.testutils.cases import TestCase


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
                message='foobar failed',
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
        assert testcase_list[0].message == 'foobar failed'
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

        teststat = ItemStat.query.filter(
            ItemStat.name == 'test_count',
            ItemStat.item_id == jobstep.id,
        )[0]
        assert teststat.value == 2

        teststat = ItemStat.query.filter(
            ItemStat.name == 'test_failures',
            ItemStat.item_id == jobstep.id,
        )[0]
        assert teststat.value == 1

        teststat = ItemStat.query.filter(
            ItemStat.name == 'test_duration',
            ItemStat.item_id == jobstep.id,
        )[0]
        assert teststat.value == 168

        teststat = ItemStat.query.filter(
            ItemStat.name == 'test_rerun_count',
            ItemStat.item_id == jobstep.id,
        )[0]
        assert teststat.value == 1
