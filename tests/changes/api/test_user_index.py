from changes.testutils import APITestCase


class UserListTest(APITestCase):
    path = '/api/0/users/'

    def test_simple(self):
        user_1 = self.create_user(email='foo@example.com', is_admin=True)
        user_2 = self.create_user(email='bar@example.com', is_admin=False)

        resp = self.client.get(self.path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == user_2.id.hex
        assert data[1]['id'] == user_1.id.hex

        resp = self.client.get(self.path + '?is_admin=1')
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == user_1.id.hex

        resp = self.client.get(self.path + '?is_admin=0')
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == user_2.id.hex

        resp = self.client.get(self.path + '?query=foo')
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == user_1.id.hex
