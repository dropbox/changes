from changes.config import db
from changes.constants import Result
from changes.models import TestSuite, AggregateTestGroup
from changes.models.testresult import TestResult, TestResultManager
from changes.testutils.cases import TestCase


class TestResultManagerTestCase(TestCase):
    def test_simple(self):
        from changes.models import TestCase, TestGroup

        build = self.create_build(self.project)
        suite = TestSuite(name='foobar', build=build, project=self.project)

        db.session.add(suite)

        results = [
            TestResult(
                build=build,
                suite=suite,
                name='test_bar',
                package='tests.changes.handlers.test_xunit',
                result=Result.failed,
                message='collection failed',
                duration=156,
            ),
            TestResult(
                build=build,
                suite=suite,
                name='test_foo',
                package='tests.changes.handlers.test_coverage',
                result=Result.passed,
                message='foobar failed',
                duration=12,
            ),
        ]
        manager = TestResultManager(build)
        manager.save(results)

        testcase_list = sorted(TestCase.query.all(), key=lambda x: x.package)

        assert len(testcase_list) == 2

        for test in testcase_list:
            assert test.build == build
            assert test.project == self.project
            assert test.suite == suite

        assert testcase_list[0].name == 'test_foo'
        assert testcase_list[0].package == 'tests.changes.handlers.test_coverage'
        assert testcase_list[0].result == Result.passed
        assert testcase_list[0].message == 'foobar failed'
        assert testcase_list[0].duration == 12

        assert len(testcase_list[0].groups) == 1

        assert testcase_list[1].name == 'test_bar'
        assert testcase_list[1].package == 'tests.changes.handlers.test_xunit'
        assert testcase_list[1].result == Result.failed
        assert testcase_list[1].message == 'collection failed'
        assert testcase_list[1].duration == 156

        group_list = sorted(TestGroup.query.all(), key=lambda x: x.name)

        assert len(group_list) == 4

        for group in group_list:
            assert group.build == build
            assert group.project == self.project
            assert group.suite == suite

        assert group_list[0].name == 'tests.changes.handlers.test_coverage'
        assert group_list[0].duration == 12
        assert group_list[0].num_tests == 1
        assert group_list[0].num_failed == 0
        assert group_list[0].result == Result.passed
        assert group_list[0].num_leaves == 1

        assert list(group_list[0].testcases) == []

        assert group_list[1].name == 'tests.changes.handlers.test_coverage.test_foo'
        assert group_list[1].duration == 12
        assert group_list[1].num_tests == 1
        assert group_list[1].num_failed == 0
        assert group_list[1].result == Result.passed
        assert group_list[1].num_leaves == 0

        assert list(group_list[1].testcases) == [testcase_list[0]]

        assert group_list[2].name == 'tests.changes.handlers.test_xunit'
        assert group_list[2].duration == 156
        assert group_list[2].num_tests == 1
        assert group_list[2].num_failed == 1
        assert group_list[2].result == Result.failed
        assert group_list[2].num_leaves == 1

        assert list(group_list[2].testcases) == []

        assert group_list[3].name == 'tests.changes.handlers.test_xunit.test_bar'
        assert group_list[3].duration == 156
        assert group_list[3].num_tests == 1
        assert group_list[3].num_failed == 1
        assert group_list[3].result == Result.failed
        assert group_list[3].num_leaves == 0

        assert list(group_list[3].testcases) == [testcase_list[1]]

        agg_groups = sorted(AggregateTestGroup.query.all(), key=lambda x: x.name)

        assert len(agg_groups) == 4

        for agg in agg_groups:
            # assert agg.last_build == build
            assert agg.first_build == build
            assert agg.project == self.project

        assert agg_groups[0].name == 'tests.changes.handlers.test_coverage'
        assert agg_groups[1].name == 'tests.changes.handlers.test_coverage.test_foo'
        assert agg_groups[2].name == 'tests.changes.handlers.test_xunit'
        assert agg_groups[3].name == 'tests.changes.handlers.test_xunit.test_bar'
