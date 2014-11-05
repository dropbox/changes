from uuid import uuid4

from changes.config import db
from changes.constants import Result, Status
from changes.testutils import APITestCase


class JobStepHeartbeatTest(APITestCase):
    def test_invalid_id(self):
        path = '/api/0/jobsteps/{0}/heartbeat/'.format(uuid4().hex)

        resp = self.client.post(path)
        assert resp.status_code == 404

    def test_simple(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(
            jobphase, status=Status.queued, result=Result.unknown,
            date_started=None, date_finished=None)

        path = '/api/0/jobsteps/{0}/heartbeat/'.format(jobstep.id.hex)

        resp = self.client.post(path)
        assert resp.status_code == 200

        jobstep.result = Result.aborted
        db.session.add(jobstep)
        db.session.flush()

        resp = self.client.post(path)
        assert resp.status_code == 410
