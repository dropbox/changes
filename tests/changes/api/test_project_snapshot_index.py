from uuid import uuid4

from changes.testutils import APITestCase


class ProjectSnapshotListTest(APITestCase):
    def _create_snapshot_post(self, project):
        path = '/api/0/projects/{0}/snapshots/'.format(project.id.hex)
        return self.unserialize(self.client.post(path))

    def test_simple(self):
        fake_project_id = uuid4()

        project = self.create_project()
        self._create_snapshot_post(project)

        project = self.create_project()
        snapshot = self._create_snapshot_post(project)

        path = '/api/0/projects/{0}/snapshots/'.format(fake_project_id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 404

        path = '/api/0/projects/{0}/snapshots/'.format(project.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == snapshot['id']
