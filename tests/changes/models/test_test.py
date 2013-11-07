from changes.constants import Result
from changes.models.test import TestResult
from changes.testutils.cases import TestCase


class TestResultTestCase(TestCase):
    def test_simple(self):
        build = self.create_build(self.project)
        result = TestResult(
            build=build,
            suite_name='foobar',
            name='Test',
            package='tests.changes.handlers.test_xunit',
            result=Result.failed,
            message='collection failed',
            duration=156,
        )
        test = result.save()

        assert test.build == build
        assert test.project == self.project
        assert test.name == 'Test'
        assert test.package == 'tests.changes.handlers.test_xunit'
        assert test.result == Result.failed
        assert test.message == 'collection failed'
        assert test.duration == 156

        suite = test.suite

        assert suite.name == 'foobar'
        assert suite.build == build
        assert suite.project == self.project

        groups = sorted(test.groups, key=lambda x: x.name)

        assert len(groups) == 2
        assert groups[0].build == build
        assert groups[0].project == self.project
        assert groups[0].name == 'tests.changes.handlers.test_xunit'
        assert groups[0].duration == 156
        assert groups[0].num_tests == 1
        assert groups[0].num_failed == 1
        assert groups[0].result == Result.failed

        assert groups[1].build == build
        assert groups[1].project == self.project
        assert groups[1].name == 'tests.changes.handlers.test_xunit.Test'
        assert groups[1].duration == 156
        assert groups[1].num_tests == 1
        assert groups[1].num_failed == 1
        assert groups[1].result == Result.failed
