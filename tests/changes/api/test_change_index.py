from changes.testutils import APITestCase


class ChangeListTest(APITestCase):
    def test_simple(self):
        change = self.create_change(self.project)
        change2 = self.create_change(self.project2)

        resp = self.client.get('/api/0/changes/')
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data['changes']) == 2
        assert data['changes'][0]['id'] == change2.id.hex
        assert data['changes'][1]['id'] == change.id.hex
