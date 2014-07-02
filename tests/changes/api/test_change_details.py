from changes.testutils import APITestCase


class ChangeDetailsTest(APITestCase):
    def test_simple(self):
        project = self.create_project()
        change = self.create_change(project)

        path = '/api/0/changes/{0}/'.format(change.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == change.id.hex
