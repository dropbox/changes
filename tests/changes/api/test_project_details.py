from changes.testutils import APITestCase


class ProjectDetailsTest(APITestCase):
    def test_simple(self):
        path = '/api/0/projects/{0}/'.format(
            self.project.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['project']['id'] == self.project.id.hex
