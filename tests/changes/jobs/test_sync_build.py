from __future__ import absolute_import

import mock

from datetime import datetime

from changes.constants import Status, Result
from changes.config import db
from changes.models import Build, ItemStat
from changes.jobs.sync_build import sync_build
from changes.testutils import TestCase


class SyncBuildTest(TestCase):
    @mock.patch('changes.config.queue.delay')
    def test_simple(self, queue_delay):
        project = self.create_project()
        build = self.create_build(
            project=project,
            status=Status.unknown,
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
            status=Status.in_progress,
            result=Result.passed,
            duration=5000,
            date_started=datetime(2013, 9, 19, 22, 15, 23),
            date_finished=datetime(2013, 9, 19, 22, 15, 26),
        )
        self.create_task(
            task_name='sync_job',
            parent_id=build.id,
            task_id=job_a.id,
            status=Status.finished,
        )
        task_b = self.create_task(
            task_name='sync_job',
            parent_id=build.id,
            task_id=job_b.id,
            status=Status.in_progress,
        )

        db.session.add(ItemStat(item_id=job_a.id, name='tests_missing', value=1))
        db.session.add(ItemStat(item_id=job_b.id, name='tests_missing', value=0))
        db.session.commit()

        sync_build(build_id=build.id.hex, task_id=build.id.hex)

        build = Build.query.get(build.id)

        assert build.status == Status.in_progress
        assert build.result == Result.failed

        task_b.status = Status.finished
        db.session.add(task_b)
        job_b.status = Status.finished
        db.session.add(job_b)
        db.session.commit()

        sync_build(build_id=build.id.hex, task_id=build.id.hex)

        build = Build.query.get(build.id)

        assert build.status == Status.finished
        assert build.result == Result.failed
        assert build.duration == 4000
        assert build.date_started == datetime(2013, 9, 19, 22, 15, 22)
        assert build.date_finished == datetime(2013, 9, 19, 22, 15, 26)

        queue_delay.assert_any_call('update_project_stats', kwargs={
            'project_id': project.id.hex,
        }, countdown=1)

        stat = ItemStat.query.filter(
            ItemStat.item_id == build.id,
            ItemStat.name == 'tests_missing',
        ).first()
        assert stat.value == 1
