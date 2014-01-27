from datetime import datetime

from changes.constants import Status
from changes.testutils import APITestCase


class BuildDetailsTest(APITestCase):
    def test_simple(self):
        previous_build = self.create_build(
            self.project, date_created=datetime(2013, 9, 19, 22, 15, 23),
            status=Status.finished)
        build = self.create_build(
            self.project, date_created=datetime(2013, 9, 19, 22, 15, 24))
        job1 = self.create_job(build)
        job2 = self.create_job(build)

        path = '/api/0/builds/{0}/'.format(build.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['build']['id'] == build.id.hex
        assert data['project']['id'] == self.project.id.hex
        assert len(data['jobs']) == 2
        assert data['jobs'][0]['id'] == job1.id.hex
        assert data['jobs'][1]['id'] == job2.id.hex
        assert len(data['previousRuns']) == 1
        assert data['previousRuns'][0]['id'] == previous_build.id.hex
        assert data['seenBy'] == []
        assert data['testFailures']['total'] == 0
        assert data['testFailures']['testGroups'] == []
