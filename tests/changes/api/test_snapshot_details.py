from changes.config import db
from changes.models import ProjectOption, Snapshot, SnapshotStatus
from changes.testutils import APITestCase


class SnapshotDetailsTest(APITestCase):
    def test_simple(self):
        project = self.create_project()
        snapshot = self.create_snapshot(project)

        path = '/api/0/snapshots/{0}/'.format(snapshot.id)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == snapshot.id.hex
        assert data['project']['id'] == project.id.hex
        assert data['build'] is None


class UpdateSnapshotTest(APITestCase):
    def setUp(self):
        super(UpdateSnapshotTest, self).setUp()
        self.project = self.create_project()
        self.snapshot = self.create_snapshot(self.project)
        self.path = '/api/0/snapshots/{0}/'.format(self.snapshot.id.hex)

    def test_simple(self):
        for status in ('active', 'failed', 'invalidated'):
            resp = self.client.post(self.path, data={
                'status': status,
            })

            assert resp.status_code == 200
            data = self.unserialize(resp)
            assert data['id'] == self.snapshot.id.hex
            assert data['status']['id'] == status
            db.session.expire(self.snapshot)

            snapshot = Snapshot.query.get(self.snapshot.id)
            assert snapshot.status == SnapshotStatus[status]

    def test_invalid_status(self):
        resp = self.client.post(self.path, data={
            'status': 'invalid_status',
        })
        assert resp.status_code == 400

    def test_set_current(self):
        for status in ('failed', 'invalidated', 'active'):
            resp = self.client.post(self.path, data={
                'status': status,
                'set_current': True,
            })

            options = dict(db.session.query(
                ProjectOption.name, ProjectOption.value
            ).filter(
                ProjectOption.project == self.project,
            ))

            if status == 'active':
                assert resp.status_code == 200
                assert options.get('snapshot.current') == self.snapshot.id.hex
            else:
                assert resp.status_code == 400
                assert options.get('snapshot.current') != self.snapshot.id.hex
