from uuid import uuid4

from changes.constants import Result, Status
from changes.testutils import APITestCase


class ProjectTestDetailsTest(APITestCase):
    def test_simple(self):
        fake_id = uuid4()

        project = self.create_project()

        build = self.create_build(
            project=project,
            status=Status.finished,
            result=Result.passed,
        )
        job = self.create_job(build)

        parent_group = self.create_test(
            job=job,
            name='foo',
        )

        # invalid project id
        path = '/api/0/projects/{0}/tests/{1}/'.format(
            fake_id.hex, parent_group.name_sha)

        resp = self.client.get(path)
        assert resp.status_code == 404

        path = '/api/0/projects/{0}/tests/{1}/'.format(
            project.id.hex, fake_id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 404

        path = '/api/0/projects/{0}/tests/{1}/'.format(
            project.id.hex, parent_group.name_sha)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        # simple test for the composite primary key
        assert data['hash'] == parent_group.name_sha
        assert data['project']['id'] == parent_group.project.id.hex
        assert data['firstBuild']['id'] == build.id.hex
