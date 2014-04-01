from uuid import uuid4

from changes.constants import Result
from changes.testutils import APITestCase


class ProjectBuildSearchTest(APITestCase):
    def test_simple(self):
        fake_project_id = uuid4()

        self.create_build(self.project)

        project1 = self.create_project()
        build1 = self.create_build(project1, label='test', target='D1234',
                                   result=Result.passed)
        project2 = self.create_project()
        build2 = self.create_build(project2, label='test', target='D1234',
                                   result=Result.failed)

        path = '/api/0/projects/{0}/builds/search/?source=D1234'.format(fake_project_id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 404

        path = '/api/0/projects/{0}/builds/search/'.format(project1.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build1.id.hex

        path = '/api/0/projects/{0}/builds/search/?source=D1234'.format(project1.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build1.id.hex

        path = '/api/0/projects/{0}/builds/search/?query=D1234'.format(project1.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build1.id.hex

        path = '/api/0/projects/{0}/builds/search/?query=test'.format(project1.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build1.id.hex

        path = '/api/0/projects/{0}/builds/search/?query=something_impossible'.format(project1.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 0

        path = '/api/0/projects/{0}/builds/search/?result=passed'.format(project1.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build1.id.hex

        path = '/api/0/projects/{0}/builds/search/?result=failed'.format(project2.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build2.id.hex

        path = '/api/0/projects/{0}/builds/search/?result=aborted'.format(project1.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 0
