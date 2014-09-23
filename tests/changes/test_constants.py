from changes.constants import Result
from changes.testutils import TestCase


class ResultTest(TestCase):
    def test_unknown_greater_than_passed(self):
        assert Result.unknown > Result.passed

    def test_failed_greater_than_passed(self):
        assert Result.failed > Result.passed

    def test_aborted_greater_than_passed(self):
        assert Result.aborted > Result.passed

    def test_aborted_greater_than_failed(self):
        assert Result.aborted > Result.failed
