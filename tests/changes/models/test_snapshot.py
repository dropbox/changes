from changes.testutils.cases import TestCase
from changes.models import Snapshot, SnapshotStatus


class TestSnapshotTestCase(TestCase):
    def test_snapshot_update_status(self):
        project = self.create_project()
        plan_1 = self.create_plan(project)
        plan_2 = self.create_plan(project)
        snapshot = self.create_snapshot(project)
        snapshot_image_1 = self.create_snapshot_image(snapshot, plan_1)
        snapshot_image_2 = self.create_snapshot_image(snapshot, plan_2)

        assert Snapshot.query.get(snapshot.id).status == SnapshotStatus.unknown

        snapshot_image_1.update_status(SnapshotStatus.active)
        assert Snapshot.query.get(snapshot.id).status == SnapshotStatus.unknown

        snapshot_image_2.update_status(SnapshotStatus.active)
        assert Snapshot.query.get(snapshot.id).status == SnapshotStatus.active
