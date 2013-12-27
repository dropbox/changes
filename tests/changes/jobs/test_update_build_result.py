from __future__ import absolute_import

from datetime import datetime

from changes.constants import Status, Result
from changes.config import db
from changes.models import Build
from changes.jobs.update_build_result import update_build_result
from changes.testutils import TestCase


class UpdateBuildResultTest(TestCase):
    def test_simple(self):
        build = self.create_build(
            project=self.project,
            status=Status.in_progress,
            result=Result.unknown,
        )
        job_a = self.create_job(
            build=build,
            status=Status.finished,
            result=Result.failed,
            duration=5000,
            date_started=datetime(2013, 9, 19, 22, 15, 22),
            date_finished=datetime(2013, 9, 19, 22, 15, 25),
        )
        job_b = self.create_job(
            build=build,
            status=Status.queued,
            result=Result.passed,
            duration=5000,
            date_started=datetime(2013, 9, 19, 22, 15, 23),
            date_finished=datetime(2013, 9, 19, 22, 15, 26),
        )
        update_build_result(build_id=build.id.hex, job_id=job_a.id.hex)
        # for good measure, test without job_id as well
        update_build_result(build_id=build.id.hex)

        db.session.expire(build)

        build = Build.query.get(build.id)

        assert build.status == Status.in_progress
        assert build.result == Result.failed

        job_b.status = Status.finished
        db.session.add(job_b)

        update_build_result(build_id=build.id.hex, job_id=job_b.id.hex)

        db.session.expire(build)

        build = Build.query.get(build.id)

        assert build.status == Status.finished
        assert build.result == Result.failed
        assert build.duration == 4000
        assert build.date_started == datetime(2013, 9, 19, 22, 15, 22)
        assert build.date_finished == datetime(2013, 9, 19, 22, 15, 26)
