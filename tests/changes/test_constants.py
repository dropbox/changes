from changes.constants import Result, Status
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


class StatusTest(TestCase):
    def test_in_progress_less_than_unknown(self):
        assert Status.in_progress < Status.unknown

    def test_finished_less_than_unknown(self):
        assert Status.finished < Status.unknown

    def test_in_progress_less_than_queued(self):
        assert Status.in_progress < Status.queued

    def test_finished_greater_than_in_progress(self):
        assert Status.finished > Status.in_progress
