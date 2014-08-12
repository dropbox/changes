from uuid import uuid4

from changes.models import Snapshot
from changes.testutils import APITestCase


class ProjectSnapshotListTest(APITestCase):
    def test_invalid_project_id(self):
        fake_project_id = uuid4()

        path = '/api/0/projects/{0}/snapshots/'.format(fake_project_id.hex)

        # invalid project id
        resp = self.client.get(path)
        assert resp.status_code == 404

    def test_simple(self):
        project_1 = self.create_project()
        self.create_snapshot(project_1)

        project_2 = self.create_project()
        snapshot = self.create_snapshot(project_2)

        path = '/api/0/projects/{0}/snapshots/'.format(project_2.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == snapshot.id.hex


class CreateProjectSnapshotTest(APITestCase):
    def test_invalid_project_id(self):
        fake_project_id = uuid4()

        path = '/api/0/projects/{0}/snapshots/'.format(fake_project_id.hex)

        # invalid project id
        resp = self.client.post(path, data={
            'sha': 'a' * 40,
        })
        assert resp.status_code == 404

    def test_simple(self):
        project = self.create_project()

        path = '/api/0/projects/{0}/snapshots/'.format(project.id.hex)

        # missing sha
        resp = self.client.post(path)
        assert resp.status_code == 400

        resp = self.client.post(path, data={
            'sha': 'a' * 40,
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)

        snapshot = Snapshot.query.get(data['id'])
        assert snapshot.source.revision_sha == 'a' * 40
        assert snapshot.project_id == project.id
