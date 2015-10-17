from changes.config import db
from changes.models import SnapshotImage, SnapshotStatus
from changes.testutils import APITestCase


class SnapshotImageDetailsTest(APITestCase):
    def test_simple(self):
        project = self.create_project()
        build = self.create_build(project=project)
        snapshot = self.create_snapshot(project, build=build)
        plan = self.create_plan(project)
        image = self.create_snapshot_image(snapshot, plan)

        path = '/api/0/snapshotimages/{0}/'.format(image.id)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == image.id.hex


class UpdateSnapshotImageTest(APITestCase):
    def setUp(self):
        super(UpdateSnapshotImageTest, self).setUp()
        self.project = self.create_project()
        build = self.create_build(project=self.project)
        self.snapshot = self.create_snapshot(self.project, build=build)
        self.plan = self.create_plan(self.project)
        self.image = self.create_snapshot_image(self.snapshot, self.plan)

        self.path = '/api/0/snapshotimages/{0}/'.format(self.image.id)

    def test_simple(self):
        for status in ('active', 'failed', 'invalidated'):
            resp = self.client.post(self.path, data={
                'status': status,
            })

            assert resp.status_code == 200
            data = self.unserialize(resp)
            assert data['id'] == self.image.id.hex
            assert data['status']['id'] == status
            db.session.expire(self.image)

            image = SnapshotImage.query.get(self.image.id)
            assert image.status == SnapshotStatus[status]

    def test_invalid_status(self):
        resp = self.client.post(self.path, data={
            'status': 'invalid_status',
        })
        assert resp.status_code == 400
