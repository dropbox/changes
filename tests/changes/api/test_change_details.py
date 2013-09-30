from changes.testutils import APITestCase


class ChangeDetailsTest(APITestCase):
    def test_simple(self):
        change = self.create_change(self.project)

        path = '/api/0/changes/{0}/'.format(change.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['change']['id'] == change.id.hex
