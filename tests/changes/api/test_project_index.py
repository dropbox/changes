from changes.constants import Result, Status
from changes.models import Project
from changes.testutils import APITestCase


class ProjectListTest(APITestCase):
    def test_simple(self):
        build = self.create_build(
            self.project, status=Status.finished, result=Result.passed)

        path = '/api/0/projects/'

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == self.project.id.hex
        assert data[0]['lastBuild']['id'] == build.id.hex
        assert data[0]['lastPassingBuild']['id'] == build.id.hex
        assert data[1]['id'] == self.project2.id.hex
        assert data[1]['lastBuild'] is None
        assert data[1]['lastPassingBuild'] is None


class ProjectCreateTest(APITestCase):
    def test_simple(self):
        path = '/api/0/projects/'

        # without auth
        resp = self.client.post(path, data={
            'name': 'Foobar',
            'repository': 'ssh://example.com/foo',
        })
        assert resp.status_code == 401

        self.login_default()

        resp = self.client.post(path, data={
            'name': 'Foobar',
            'repository': 'ssh://example.com/foo',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id']
        assert data['slug'] == 'foobar'

        assert Project.query.filter(
            Project.name == 'Foobar',
        ).first()
