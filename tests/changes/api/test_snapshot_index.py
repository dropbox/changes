from changes.config import db
from changes.models import ProjectOption, SnapshotStatus
from changes.testutils import APITestCase


class SnapshotListTest(APITestCase):
    def test_simple(self):
        project_1 = self.create_project()
        build_1 = self.create_build(project_1)
        snapshot_1 = self.create_snapshot(
            project=project_1, status=SnapshotStatus.active, build=build_1)
        plan_1 = self.create_plan(project_1)
        image_1 = self.create_snapshot_image(snapshot_1, plan_1)

        project_2 = self.create_project()
        build_2 = self.create_build(project_2)
        snapshot_2 = self.create_snapshot(
            project=project_2, status=SnapshotStatus.invalidated, build=build_2)
        plan_2 = self.create_plan(project_2)
        image_2 = self.create_snapshot_image(snapshot_2, plan_1)
        image_3 = self.create_snapshot_image(snapshot_2, plan_2)

        db.session.add(ProjectOption(
            project=project_2,
            name='snapshot.current',
            value=snapshot_2.id.hex,
        ))
        db.session.commit()

        path = '/api/0/snapshots/?state='

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == snapshot_2.id.hex
        assert data[0]['isActive']
        assert len(data[0]['images']) == 2
        assert data[0]['images'][0]['id'] == image_2.id.hex
        assert data[0]['images'][1]['id'] == image_3.id.hex

        assert data[1]['id'] == snapshot_1.id.hex
        assert not data[1]['isActive']
        assert len(data[1]['images']) == 1
        assert data[1]['images'][0]['id'] == image_1.id.hex

        path = '/api/0/snapshots/?state=valid'

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == snapshot_1.id.hex

        path = '/api/0/snapshots/?state=invalid'

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == snapshot_2.id.hex
