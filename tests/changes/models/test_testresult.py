from changes.config import db
from changes.constants import Result
from changes.models import ItemStat, TestSuite
from changes.models.testresult import TestResult, TestResultManager
from changes.testutils.cases import TestCase


class TestResultManagerTestCase(TestCase):
    def test_simple(self):
        from changes.models import TestCase

        build = self.create_build(self.project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)
        suite = TestSuite(name='foobar', job=job, project=self.project)

        db.session.add(suite)
        db.session.commit()

        results = [
            TestResult(
                step=jobstep,
                suite=suite,
                name='test_bar',
                package='tests.changes.handlers.test_xunit',
                result=Result.failed,
                message='collection failed',
                duration=156,
            ),
            TestResult(
                step=jobstep,
                suite=suite,
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
            assert test.project_id == self.project.id
            assert test.suite_id == suite.id

        assert testcase_list[0].name == 'tests.changes.handlers.test_coverage.test_foo'
        assert testcase_list[0].result == Result.passed
        assert testcase_list[0].message == 'foobar failed'
        assert testcase_list[0].duration == 12
        assert testcase_list[0].reruns == 1

        assert testcase_list[1].name == 'tests.changes.handlers.test_xunit.test_bar'
        assert testcase_list[1].result == Result.failed
        assert testcase_list[1].message == 'collection failed'
        assert testcase_list[1].duration == 156
        assert testcase_list[1].reruns is None

        teststat = ItemStat.query.filter(
            ItemStat.name == 'test_count',
            ItemStat.item_id == build.id,
        )[0]
        assert teststat.value == 2

        teststat = ItemStat.query.filter(
            ItemStat.name == 'test_count',
            ItemStat.item_id == job.id,
        )[0]
        assert teststat.value == 2

        teststat = ItemStat.query.filter(
            ItemStat.name == 'test_duration',
            ItemStat.item_id == build.id,
        )[0]
        assert teststat.value == 168

        teststat = ItemStat.query.filter(
            ItemStat.name == 'test_duration',
            ItemStat.item_id == job.id,
        )[0]
        assert teststat.value == 168

        job2 = self.create_job(build)
        jobphase2 = self.create_jobphase(job2)
        jobstep2 = self.create_jobstep(jobphase2)

        results2 = [
            TestResult(
                step=jobstep2,
                name='test_bar',
                package='tests.changes.handlers.test_bar',
                result=Result.failed,
                message='collection failed',
                duration=156,
            ),
        ]
        manager = TestResultManager(jobstep2)
        manager.save(results2)

        teststat = ItemStat.query.filter(
            ItemStat.name == 'test_count',
            ItemStat.item_id == build.id,
        )[0]
        assert teststat.value == 3

        teststat = ItemStat.query.filter(
            ItemStat.name == 'test_count',
            ItemStat.item_id == job2.id,
        )[0]
        assert teststat.value == 1

        teststat = ItemStat.query.filter(
            ItemStat.name == 'test_duration',
            ItemStat.item_id == build.id,
        )[0]
        assert teststat.value == 324

        teststat = ItemStat.query.filter(
            ItemStat.name == 'test_duration',
            ItemStat.item_id == job2.id,
        )[0]
        assert teststat.value == 156
