from changes.testutils import APITestCase, override_config


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
        assert data['user']['id'] == self.default_user.id.hex

    def test_pp_anonymous(self):
        with override_config('PP_AUTH', True):
            resp = self.client.get(self.path)
            assert resp.status_code == 200
            data = self.unserialize(resp)
            assert data['authenticated'] is False

    def test_pp_authenticated(self):
        with override_config('PP_AUTH', True):
            resp = self.client.get(self.path, headers={'X-PP-USER': self.default_user.email})
            assert resp.status_code == 200
            data = self.unserialize(resp)
            assert data['authenticated'] is True
            assert data['user']['id'] == self.default_user.id.hex
