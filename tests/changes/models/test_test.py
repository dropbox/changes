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
            result=Result.skipped,
            message='collection skipped',
            duration=156,
        )
        test = result.save()

        assert test.build == build
        assert test.project == self.project
        assert test.name == 'Test'
        assert test.package == 'tests.changes.handlers.test_xunit'
        assert test.result == Result.skipped
        assert test.message == 'collection skipped'
        assert test.duration == 156

        suite = test.suite

        assert suite.name == 'foobar'
        assert suite.build == build
        assert suite.project == self.project

        groups = list(test.groups)

        assert len(groups) == 1
        assert groups[0].build == build
        assert groups[0].project == self.project
        assert groups[0].name == 'tests.changes.handlers.test_xunit'
        assert groups[0].duration == 156
        assert groups[0].num_tests == 1
        assert groups[0].num_failed == 0
        assert groups[0].result == Result.skipped
