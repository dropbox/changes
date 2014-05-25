from changes.testutils import APITestCase


class PatchDetailsTest(APITestCase):
    def test_simple(self):
        patch = self.create_patch(self.project)

        path = '/api/0/patches/{0}/'.format(patch.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == patch.id.hex

    def test_raw(self):
        patch = self.create_patch(self.project)

        path = '/api/0/patches/{0}/?raw=1'.format(patch.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        assert resp.data == patch.diff.encode('utf-8')
