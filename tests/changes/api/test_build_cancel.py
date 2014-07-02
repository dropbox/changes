import mock

from changes.constants import Result, Status
from changes.models import Build, Step
from changes.testutils import APITestCase


class BuildCancelTest(APITestCase):
    @mock.patch.object(Step, 'get_implementation')
    def test_simple(self, get_implementation):
        project = self.create_project()

        implementation = mock.Mock()
        get_implementation.return_value = implementation

        build = self.create_build(
            project=project, status=Status.in_progress)
        job = self.create_job(build=build, status=Status.in_progress)
        plan = self.create_plan()
        self.create_step(plan)
        self.create_job_plan(job, plan)

        path = '/api/0/builds/{0}/cancel/'.format(build.id.hex)
        resp = self.client.post(path, follow_redirects=True)

        assert resp.status_code == 200

        data = self.unserialize(resp)

        assert data['id'] == build.id.hex

        implementation.cancel.assert_called_once_with(job=job)

        build = Build.query.get(build.id)

        assert build.status == Status.finished
        assert build.result == Result.aborted
