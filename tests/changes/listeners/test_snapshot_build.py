from __future__ import absolute_import

from changes.constants import Cause, Result, Status
from changes.listeners.snapshot_build import build_finished_handler
from changes.models import SnapshotStatus
from changes.testutils import TestCase


class SnapshotBuildTest(TestCase):
    def test_simple(self):
        project = self.create_project()
        build = self.create_build(project, cause=Cause.snapshot, result=Result.failed, status=Status.finished)
        snapshot = self.create_snapshot(project, build=build, status=SnapshotStatus.pending)
        build_finished_handler(build_id=build.id.hex)
        assert snapshot.status == SnapshotStatus.failed

    def test_invalidate(self):
        project = self.create_project()
        build = self.create_build(project, cause=Cause.snapshot, result=Result.failed, status=Status.finished)
        snapshot = self.create_snapshot(project, build=build, status=SnapshotStatus.active)
        build_finished_handler(build_id=build.id.hex)
        assert snapshot.status == SnapshotStatus.invalidated
