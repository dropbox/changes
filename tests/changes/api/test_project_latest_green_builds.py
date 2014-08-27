from uuid import uuid4

from changes.constants import Result
from changes.testutils import APITestCase


class ProjectLatestGreenBuildTest(APITestCase):
    def test_simple(self):
        fake_project_id = uuid4()

        project = self.create_project()
        self.create_build(project)

        project1 = self.create_project()
        build1 = self.create_build(project1, label='test', target='D1234',
                                   result=Result.passed)
        project2 = self.create_project()
        build2 = self.create_build(project2, label='test2', target='D1234',
                                   result=Result.failed)

        self.create_latest_green_build(project=project2,
                                       build=build2,
                                       branch='master')

        project3 = self.create_project()
        build3 = self.create_build(project3, label='test3', target='D1234',
                                   result=Result.failed)
        build4 = self.create_build(project3, label='test4', target='D1234',
                                   result=Result.failed)

        self.create_latest_green_build(project=project3,
                                       build=build3,
                                       branch='master')

        self.create_latest_green_build(project=project3,
                                       build=build4,
                                       branch='other')

        path = '/api/0/projects/{0}/latest_green_builds/'.format(fake_project_id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 404

        path = '/api/0/projects/{0}/latest_green_builds/'.format(project1.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 0

        path = '/api/0/projects/{0}/latest_green_builds/'.format(project2.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1

        path = '/api/0/projects/{0}/latest_green_builds/'.format(project3.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2

        path = '/api/0/projects/{0}/latest_green_builds/?branch=master'.format(project3.id.hex)
        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
