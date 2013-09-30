from changes.models import Change
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


class ChangeCreateTest(APITestCase):
    def test_simple(self):
        change = self.create_change(self.project)
        path = '/api/0/changes/'.format(change.id.hex)
        resp = self.client.post(path, data={
            'project': self.project.slug,
            'label': 'D1234',
            'sha': 'a' * 40,
            'author': 'David Cramer <dcramer@example.com>',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['change']['id']
        change = Change.query.get(data['change']['id'])
        assert change.project == self.project
        assert change.label == 'D1234'
        assert change.revision_sha == 'a' * 40
        assert change.author.name == 'David Cramer'
        assert change.author.email == 'dcramer@example.com'
