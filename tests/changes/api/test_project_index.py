from changes.constants import Status
from changes.testutils import APITestCase


class ProjectListTest(APITestCase):
    def test_simple(self):
        build = self.create_build(self.project, status=Status.finished)

        path = '/api/0/projects/'.format(
            self.project.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == self.project.id.hex
        assert data[0]['lastBuild']['id'] == build.id.hex
        assert data[1]['id'] == self.project2.id.hex
        assert data[1]['lastBuild'] is None
