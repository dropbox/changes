from changes.config import db
from changes.testutils.cases import TestCase
from changes.models import ProjectOption, Snapshot, SnapshotImage, SnapshotStatus


class TestSnapshotTestCase(TestCase):
    def test_snapshot_change_status(self):
        project = self.create_project()
        plan_1 = self.create_plan(project)
        plan_2 = self.create_plan(project)
        snapshot = self.create_snapshot(project, status=SnapshotStatus.pending)
        snapshot_image_1 = self.create_snapshot_image(snapshot, plan_1)
        snapshot_image_2 = self.create_snapshot_image(snapshot, plan_2)

        assert Snapshot.query.get(snapshot.id).status == SnapshotStatus.pending

        snapshot_image_1.change_status(SnapshotStatus.active)
        assert Snapshot.query.get(snapshot.id).status == SnapshotStatus.pending

        snapshot_image_2.change_status(SnapshotStatus.active)
        assert Snapshot.query.get(snapshot.id).status == SnapshotStatus.active

    def test_snapshot_invalidated(self):
        project = self.create_project()
        plan_1 = self.create_plan(project)
        plan_2 = self.create_plan(project)
        snapshot = self.create_snapshot(project, status=SnapshotStatus.pending)
        snapshot_image_1 = self.create_snapshot_image(snapshot, plan_1)
        snapshot_image_2 = self.create_snapshot_image(snapshot, plan_2)

        snapshot_image_1.change_status(SnapshotStatus.active)
        snapshot_image_2.change_status(SnapshotStatus.active)
        snapshot_image_1.change_status(SnapshotStatus.invalidated)

        assert Snapshot.query.get(snapshot.id).status == SnapshotStatus.invalidated

    def test_snapshot_failed(self):
        project = self.create_project()
        plan_1 = self.create_plan(project)
        plan_2 = self.create_plan(project)
        snapshot = self.create_snapshot(project, status=SnapshotStatus.failed)
        snapshot_image_1 = self.create_snapshot_image(snapshot, plan_1)
        snapshot_image_2 = self.create_snapshot_image(snapshot, plan_2)

        snapshot_image_1.change_status(SnapshotStatus.active)
        snapshot_image_2.change_status(SnapshotStatus.active)

        assert Snapshot.query.get(snapshot.id).status == SnapshotStatus.failed


class TestSnapshotImageTestCase(TestCase):
    def test_get_snapshot_image_independent(self):
        project = self.create_project()
        plan = self.create_plan(project)
        snapshot = self.create_snapshot(project)
        db.session.add(ProjectOption(
            project_id=project.id,
            name='snapshot.current',
            value=snapshot.id.hex,
        ))
        snapshot_image = self.create_snapshot_image(snapshot, plan)

        assert snapshot_image == SnapshotImage.get_current(plan)

    def test_get_snapshot_image_dependent(self):
        project = self.create_project()
        plan_1 = self.create_plan(project)
        plan_2 = self.create_plan(project)
        plan_1.snapshot_plan_id = plan_2.id
        snapshot = self.create_snapshot(project)
        db.session.add(ProjectOption(
            project_id=project.id,
            name='snapshot.current',
            value=snapshot.id.hex,
        ))
        snapshot_image_1 = self.create_snapshot_image(snapshot, plan_1)
        snapshot_image_2 = self.create_snapshot_image(snapshot, plan_2)

        assert snapshot_image_2 == SnapshotImage.get_current(plan_1)
        assert snapshot_image_2 == SnapshotImage.get_current(plan_2)
