from changes.testutils import APITestCase


class ProjectSourceDetailsTest(APITestCase):
    def test_simple(self):
        source = self.create_source(self.project)

        path = '/api/0/projects/{0}/sources/{1}/'.format(
            self.project.id.hex, source.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == source.id.hex
