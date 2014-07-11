from changes.models import User
from changes.testutils import APITestCase


class UserDetailsTest(APITestCase):
    def test_simple(self):
        user = self.create_user(email='foobar@example.com')

        path = '/api/0/users/{0}/'.format(user.id)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == user.id.hex


class UpdateUserTest(APITestCase):
    def test_simple(self):
        user = self.create_user(
            email='foobar@example.com',
            is_admin=False,
        )

        path = '/api/0/users/{0}/'.format(user.id)

        # ensure endpoint requires authentication
        resp = self.client.post(path, data={
            'is_admin': '1'
        })
        assert resp.status_code == 401

        self.login_default()

        # ensure endpoint requires admin
        resp = self.client.post(path, data={
            'is_admin': '1'
        })
        assert resp.status_code == 403

        self.login_default_admin()

        # test setting is_admin
        resp = self.client.post(path, data={
            'is_admin': '1'
        })
        assert resp.status_code == 200

        data = self.unserialize(resp)
        assert data['isAdmin'] is True

        user = User.query.get(user.id)
        assert user.is_admin is True
