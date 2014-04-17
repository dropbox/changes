from uuid import uuid4

from changes.constants import Result, Status
from changes.testutils import APITestCase


class ProjectTestIndexTest(APITestCase):
    def test_simple(self):
        fake_project_id = uuid4()

        build = self.create_build(self.project)
        self.create_job(build)

        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(
            build, status=Status.finished, result=Result.passed)

        self.create_test(job=job, name='foo.bar', duration=50)
        self.create_test(job=job, name='foo.baz', duration=70)
        self.create_test(job=job, name='blah.blah', duration=10)

        path = '/api/0/projects/{0}/testgroups/'.format(fake_project_id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 404

        path = '/api/0/projects/{0}/testgroups/'.format(project.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data['groups']) == 2
        assert data['groups'][0]['name'] == 'foo'
        assert data['groups'][0]['path'] == 'foo'
        assert data['groups'][0]['numTests'] == 2
        assert data['groups'][0]['totalDuration'] == 120
        assert data['groups'][1]['name'] == 'blah.blah'
        assert data['groups'][1]['path'] == 'blah.blah'
        assert data['groups'][1]['numTests'] == 1
        assert data['groups'][1]['totalDuration'] == 10
        assert len(data['trail']) == 0

        path = '/api/0/projects/{0}/testgroups/?parent=foo'.format(project.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data['groups']) == 2
        assert data['groups'][0]['name'] == 'baz'
        assert data['groups'][0]['path'] == 'foo.baz'
        assert data['groups'][0]['numTests'] == 1
        assert data['groups'][0]['totalDuration'] == 70
        assert data['groups'][1]['name'] == 'bar'
        assert data['groups'][1]['path'] == 'foo.bar'
        assert data['groups'][1]['numTests'] == 1
        assert data['groups'][1]['totalDuration'] == 50
        assert len(data['trail']) == 1
        assert data['trail'][0] == {
            'name': 'foo',
            'path': 'foo',
        }
