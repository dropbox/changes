import mock

from changes.config import db
from changes.constants import Result, Status
from changes.models import Build
from changes.testutils import APITestCase


class BuildRestartTest(APITestCase):
    @mock.patch('changes.api.build_restart.execute_build')
    def test_simple(self, execute_build):
        build = self.create_build(
            project=self.project, status=Status.in_progress)

        path = '/api/0/builds/{0}/restart/'.format(build.id.hex)

        # build isnt finished
        resp = self.client.post(path, follow_redirects=True)
        assert resp.status_code == 400

        build.status = Status.finished
        db.session.add(build)

        resp = self.client.post(path, follow_redirects=True)
        assert resp.status_code == 200

        data = self.unserialize(resp)

        assert data['id'] == build.id.hex

        execute_build.assert_called_once_with(build=build)

        build = Build.query.get(build.id)

        assert build.status == Status.queued
        assert build.result == Result.unknown
        assert build.date_finished is None
        assert build.duration is None
