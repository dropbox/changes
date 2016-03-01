from uuid import uuid4

from changes.constants import Result, Status
from changes.testutils import APITestCase


class BuildTestIndexTest(APITestCase):
    def test_owner_extraction(self):
        fake_id = uuid4()

        test_id_a = 'a' * 32
        test_id_b = 'b' * 32

        email = 'Foo <foo@example.com>'
        owner = 'foo'
        author = self.create_author(email)
        project = self.create_project()
        build = self.create_build(project, result=Result.failed, author=author)
        job = self.create_job(build, status=Status.finished)
        plan = self.create_plan(project)
        step = self.create_step(plan)
        test = self.create_test(job, reruns=2, result=Result.passed, id=test_id_a)
        test = self.create_test(job, reruns=2, result=Result.passed, id=test_id_b, owner=owner)

        # Ensure bad queries return 404.
        path = '/api/0/builds/{0}/flaky_tests/'.format('c' * 32)
        resp = self.client.get(path)
        assert resp.status_code == 404

        # Ensure good queries return an appropriate, structured response.
        path = '/api/0/builds/{0}/flaky_tests/'.format(build.id.hex)
        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)

        assert data['flakyTests']['count'] == 2

        # flakyTests results seem to come in nondeterministic order, so make
        # sure we can handle that.
        expected_results = {
            test_id_a: email,
            test_id_b: owner,
        }

        received_ids = []
        for flaky_test in data['flakyTests']['items']:
            test_id = flaky_test['id']
            received_ids.append(test_id)
            assert flaky_test['author']['email'] == expected_results[test_id]

        # Ensure that we saw every test id we expected to see.
        assert set(received_ids) == set(expected_results.keys())
