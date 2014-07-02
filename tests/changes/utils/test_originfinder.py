from datetime import datetime

from changes.constants import Result, Status
from changes.testutils import TestCase
from changes.utils.originfinder import find_failure_origins


class FindFailureOriginsTest(TestCase):
    def test_simple(self):
        project = self.create_project()
        source = self.create_source(project)
        build_a = self.create_build(
            project=project, result=Result.passed, status=Status.finished,
            label='build a', date_created=datetime(2013, 9, 19, 22, 15, 22),
            source=source)
        job_a = self.create_job(build=build_a)
        build_b = self.create_build(
            project=project, result=Result.failed, status=Status.finished,
            label='build b', date_created=datetime(2013, 9, 19, 22, 15, 23),
            source=source)
        job_b = self.create_job(build=build_b)
        build_c = self.create_build(
            project=project, result=Result.failed, status=Status.finished,
            label='build c', date_created=datetime(2013, 9, 19, 22, 15, 24),
            source=source)
        job_c = self.create_job(build=build_c)
        build_d = self.create_build(
            project=project, result=Result.failed, status=Status.finished,
            label='build d', date_created=datetime(2013, 9, 19, 22, 15, 25),
            source=source)
        job_d = self.create_job(build=build_d)

        self.create_test(job_a, name='foo', result=Result.passed)
        self.create_test(job_a, name='bar', result=Result.passed)
        self.create_test(job_b, name='foo', result=Result.failed)
        self.create_test(job_b, name='bar', result=Result.passed)
        self.create_test(job_c, name='foo', result=Result.failed)
        self.create_test(job_c, name='bar', result=Result.failed)
        foo_d = self.create_test(job_d, name='foo', result=Result.failed)
        bar_d = self.create_test(job_d, name='bar', result=Result.failed)

        result = find_failure_origins(build_d, [foo_d, bar_d])
        assert result == {
            foo_d: build_b,
            bar_d: build_c
        }
