from changes.constants import Result, Status
from changes.models import Project
from changes.testutils import APITestCase


class ProjectListTest(APITestCase):
    def test_simple(self):
        project_1 = self.create_project(name='test1')
        project_2 = self.create_project(name='test2')
        project_3 = self.create_project(name='zzz')

        build_1 = self.create_build(
            project_1, status=Status.finished, result=Result.passed)
        build_2 = self.create_build(
            project_2, status=Status.finished, result=Result.failed)

        path = '/api/0/projects/'

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 3
        assert data[0]['id'] == project_1.id.hex
        assert data[0]['lastBuild']['id'] == build_1.id.hex
        assert data[0]['lastPassingBuild']['id'] == build_1.id.hex
        assert data[1]['id'] == project_2.id.hex
        assert data[1]['lastBuild']['id'] == build_2.id.hex
        assert data[1]['lastPassingBuild'] is None
        assert data[2]['id'] == project_3.id.hex
        assert data[2]['lastBuild'] is None
        assert data[2]['lastPassingBuild'] is None


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
