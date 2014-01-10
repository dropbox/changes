from __future__ import absolute_import

import mock

from datetime import datetime

from changes.config import queue
from changes.constants import Result, Status
from changes.jobs.cleanup_jobs import (
    cleanup_jobs, EXPIRE_BUILDS, CHECK_BUILDS)
from changes.models import Job
from changes.testutils import TestCase


class CleanupJobsTest(TestCase):
    @mock.patch.object(queue, 'delay')
    def test_expires_jobs(self, queue_delay):
        dt = datetime.utcnow() - (EXPIRE_BUILDS * 2)

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            date_created=dt,
            status=Status.queued,
        )

        cleanup_jobs()

        assert not queue_delay.called

        job = Job.query.filter(
            Job.id == job.id
        ).first()

        assert job.date_modified != dt
        assert job.result == Result.aborted
        assert job.status == Status.finished

    @mock.patch.object(queue, 'delay')
    def test_queues_jobs(self, queue_delay):
        dt = datetime.utcnow() - (CHECK_BUILDS * 2)

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            date_created=dt,
            status=Status.queued,
        )

        cleanup_jobs()

        queue_delay.assert_called_once_with(
            'sync_job', kwargs={'job_id': job.id.hex})

        job = Job.query.filter(
            Job.id == job.id
        ).first()
        assert job.date_modified != dt

    @mock.patch.object(queue, 'delay')
    def test_ignores_recent_jobs(self, queue_delay):
        dt = datetime.utcnow()

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            date_created=dt,
            status=Status.queued,
        )

        cleanup_jobs()

        assert not queue_delay.called

        job = Job.query.filter(
            Job.id == job.id
        ).first()
        assert job.date_modified == dt
