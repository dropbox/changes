from datetime import datetime

from changes.constants import Result, Status
from changes.testutils import TestCase
from changes.utils.originfinder import find_failure_origins


class FindFailureOriginsTest(TestCase):
    def test_simple(self):
        job_a = self.create_job(
            self.project, result=Result.passed, status=Status.finished,
            label='job a', date_created=datetime(2013, 9, 19, 22, 15, 22))
        job_b = self.create_job(
            self.project, result=Result.failed, status=Status.finished,
            label='job b', date_created=datetime(2013, 9, 19, 22, 15, 23))
        job_c = self.create_job(
            self.project, result=Result.failed, status=Status.finished,
            label='job c', date_created=datetime(2013, 9, 19, 22, 15, 24))
        job_d = self.create_job(
            self.project, result=Result.failed, status=Status.finished,
            label='job d', date_created=datetime(2013, 9, 19, 22, 15, 25))

        self.create_testgroup(job_a, name='foo', result=Result.passed)
        self.create_testgroup(job_a, name='bar', result=Result.passed)
        self.create_testgroup(job_b, name='foo', result=Result.failed)
        self.create_testgroup(job_b, name='bar', result=Result.passed)
        self.create_testgroup(job_c, name='foo', result=Result.failed)
        self.create_testgroup(job_c, name='bar', result=Result.failed)
        foo_d = self.create_testgroup(job_d, name='foo', result=Result.failed)
        bar_d = self.create_testgroup(job_d, name='bar', result=Result.failed)

        result = find_failure_origins(job_d, [foo_d, bar_d])
        assert result == {
            foo_d: job_b,
            bar_d: job_c
        }
