from changes.testutils import APITestCase


class AuthIndexTest(APITestCase):
    path = '/api/0/auth/'

    def test_anonymous(self):
        resp = self.client.get(self.path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['authenticated'] is False

    def test_authenticated(self):
        self.login_default()

        resp = self.client.get(self.path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['authenticated'] is True
        assert data['user'] == {
            'id': self.default_user.id.hex,
            'email': self.default_user.email,
        }
