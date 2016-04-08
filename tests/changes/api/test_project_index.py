from datetime import datetime

from changes.constants import Cause, Result, Status
from changes.models import Project
from changes.testutils import APITestCase


class ProjectListTest(APITestCase):
    endpoint_path = '/api/0/projects/'

    def test_simple(self):
        project1 = self.create_project(name='test1')
        project2 = self.create_project(name='test2')
        project3 = self.create_project(name='zzz')

        build1 = self.create_build(
            project1, status=Status.finished, result=Result.passed)
        build2 = self.create_build(
            project2, status=Status.finished, result=Result.failed)

        resp = self.client.get(self.endpoint_path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 3
        assert data[0]['id'] == project1.id.hex
        assert data[0]['lastBuild']['id'] == build1.id.hex
        assert data[0]['lastPassingBuild']['id'] == build1.id.hex
        assert data[1]['id'] == project2.id.hex
        assert data[1]['lastBuild']['id'] == build2.id.hex
        assert data[1]['lastPassingBuild'] is None
        assert data[2]['id'] == project3.id.hex
        assert data[2]['lastBuild'] is None
        assert data[2]['lastPassingBuild'] is None

    def test_fetch_extra(self):
        repo = self.create_repo()
        project = self.create_project(repository=repo)
        self.create_project_option(project, "foo", "bar")
        plan = self.create_plan(project)
        build = self.create_build(project, status=Status.finished, result=Result.passed)

        resp = self.client.get(self.endpoint_path + '?fetch_extra=1')
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1

        assert data[0]['id'] == project.id.hex
        assert data[0]['lastBuild']['id'] == build.id.hex
        assert data[0]['lastPassingBuild']['id'] == build.id.hex
        assert data[0]['repository']['id'] == repo.id.hex
        assert data[0]['options'] == {"foo": "bar"}
        assert len(data[0]['plans']) == 1
        assert data[0]['plans'][0]['id'] == plan.id.hex

    def test_excludes_snapshots(self):
        project = self.create_project()
        build1 = self.create_build(project, status=Status.finished, result=Result.failed)
        build2 = self.create_build(project, status=Status.finished, result=Result.passed, cause=Cause.snapshot)

        resp = self.client.get(self.endpoint_path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == project.id.hex
        assert data[0]['lastBuild']['id'] == build1.id.hex
        assert data[0]['lastPassingBuild'] is None

    def test_passing_not_latest(self):
        project = self.create_project()
        build_1 = self.create_build(project, status=Status.finished, result=Result.passed,
                                    date_created=datetime(2016, 4, 4))
        build_2 = self.create_build(project, status=Status.finished, result=Result.failed,
                                    date_created=datetime(2016, 4, 5))

        resp = self.client.get(self.endpoint_path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == project.id.hex
        assert data[0]['lastBuild']['id'] == build_2.id.hex
        assert data[0]['lastPassingBuild']['id'] == build_1.id.hex


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

        # without admin
        resp = self.client.post(path, data={
            'name': 'Foobar',
            'repository': 'ssh://example.com/foo',
        })
        assert resp.status_code == 403

        self.login_default_admin()

        # invalid repo url
        resp = self.client.post(path, data={
            'name': 'Foobar',
            'repository': 'ssh://example.com/foo',
        })
        assert resp.status_code == 400

        # valid params
        repo = self.create_repo()
        resp = self.client.post(path, data={
            'name': 'Foobar',
            'repository': repo.url,
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id']
        assert data['slug'] == 'foobar'

        assert Project.query.filter(
            Project.name == 'Foobar',
        ).first()
