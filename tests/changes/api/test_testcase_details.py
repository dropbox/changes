from changes.testutils import APITestCase


class TestCaseDetailsTest(APITestCase):
    def test_simple(self):
        project = self.create_project()
        build = self.create_build(project=project)
        job = self.create_job(build=build)

        testcase = self.create_test(job=job)

        path = '/api/0/tests/{0}/'.format(
            testcase.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == testcase.id.hex
