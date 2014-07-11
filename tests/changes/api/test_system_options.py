from changes.config import db
from changes.models import SystemOption
from changes.testutils import APITestCase


class SystemOptionsListTest(APITestCase):
    def test_simple(self):
        path = '/api/0/systemoptions/'

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['system.message'] == ''

        db.session.add(SystemOption(
            name='system.message',
            value='hello',
        ))
        db.session.commit()

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['system.message'] == 'hello'


class SystemOptionsUpdateTest(APITestCase):
    def test_simple(self):
        path = '/api/0/systemoptions/'

        resp = self.client.post(path, data={
            'system.message': 'hello',
        })
        assert resp.status_code == 401

        self.login_default()

        resp = self.client.post(path, data={
            'system.message': 'hello',
        })
        assert resp.status_code == 403

        self.login_default_admin()

        resp = self.client.post(path, data={
            'system.message': 'hello',
        })
        assert resp.status_code == 200

        options = dict(db.session.query(
            SystemOption.name, SystemOption.value
        ))

        assert options.get('system.message') == 'hello'
