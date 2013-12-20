from __future__ import absolute_import

import mock

from datetime import datetime

from changes.config import queue
from changes.constants import Result, Status
from changes.jobs.cleanup_builds import (
    cleanup_builds, EXPIRE_BUILDS, CHECK_BUILDS)
from changes.models import Build
from changes.testutils import TestCase


class CleanupBuildsTest(TestCase):
    @mock.patch.object(queue, 'delay')
    def test_expires_builds(self, queue_delay):
        dt = datetime.utcnow() - (EXPIRE_BUILDS * 2)

        build = self.create_build(
            self.project, date_created=dt, status=Status.queued)

        cleanup_builds()

        assert not queue_delay.called

        build = Build.query.filter(
            Build.id == build.id
        ).first()

        assert build.date_modified != dt
        assert build.result == Result.aborted
        assert build.status == Status.finished

    @mock.patch.object(queue, 'delay')
    def test_queues_builds(self, queue_delay):
        dt = datetime.utcnow() - (CHECK_BUILDS * 2)

        build = self.create_build(
            self.project, date_created=dt, status=Status.queued)

        cleanup_builds()

        queue_delay.assert_called_once_with(
            'sync_build', kwargs={'build_id': build.id.hex})

        build = Build.query.filter(
            Build.id == build.id
        ).first()
        assert build.date_modified != dt

    @mock.patch.object(queue, 'delay')
    def test_ignores_recent_builds(self, queue_delay):
        dt = datetime.utcnow()

        build = self.create_build(
            self.project, date_created=dt, status=Status.queued)

        cleanup_builds()

        assert not queue_delay.called

        build = Build.query.filter(
            Build.id == build.id
        ).first()
        assert build.date_modified == dt
