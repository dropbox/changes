from __future__ import absolute_import

import mock

from datetime import datetime

from changes.constants import Result, Status
from changes.jobs.cleanup_builds import (
    cleanup_builds, EXPIRE_BUILDS, CHECK_BUILDS)
from changes.jobs.sync_build import sync_build
from changes.models import Build
from changes.testutils import TestCase


class CleanupBuildsTest(TestCase):
    @mock.patch.object(sync_build, 'delay_if_needed')
    def test_expires_builds(self, sync_build_delay):
        dt = datetime.utcnow() - (EXPIRE_BUILDS * 2)

        build = self.create_build(
            project=self.project,
            date_created=dt,
            status=Status.queued,
        )

        cleanup_builds()

        assert not sync_build_delay.called

        build = Build.query.get(build.id)

        assert build.date_modified != dt
        assert build.result == Result.aborted
        assert build.status == Status.finished

    @mock.patch.object(sync_build, 'delay_if_needed')
    def test_queues_jobs(self, sync_build_delay):
        dt = datetime.utcnow() - (CHECK_BUILDS * 2)

        build = self.create_build(
            project=self.project,
            date_created=dt,
            status=Status.queued,
        )

        cleanup_builds()

        sync_build_delay.assert_called_once_with(
            build_id=build.id.hex,
            task_id=build.id.hex,
        )

        build = Build.query.get(build.id)

        assert build.date_modified != dt

    @mock.patch.object(sync_build, 'delay_if_needed')
    def test_ignores_recent_jobs(self, sync_build_delay):
        dt = datetime.utcnow()

        build = self.create_build(
            project=self.project,
            date_created=dt,
            status=Status.queued,
        )

        cleanup_builds()

        assert not sync_build_delay.called

        build = Build.query.get(build.id)

        assert build.date_modified == dt
