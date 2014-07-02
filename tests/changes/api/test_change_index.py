from changes.models import Change
from changes.testutils import APITestCase


class ChangeListTest(APITestCase):
    def test_simple(self):
        project = self.create_project()
        project2 = self.create_project()
        change = self.create_change(project)
        change2 = self.create_change(project2)

        resp = self.client.get('/api/0/changes/')
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == change2.id.hex
        assert data[1]['id'] == change.id.hex


class ChangeCreateTest(APITestCase):
    def test_simple(self):
        project = self.create_project()
        change = self.create_change(project)
        path = '/api/0/changes/'.format(change.id.hex)
        resp = self.client.post(path, data={
            'project': project.slug,
            'label': 'D1234',
            'author': 'David Cramer <dcramer@example.com>',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id']
        change = Change.query.get(data['id'])
        assert change.project == project
        assert change.label == 'D1234'
        assert change.author.name == 'David Cramer'
        assert change.author.email == 'dcramer@example.com'
