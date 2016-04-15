from __future__ import absolute_import

import json

from changes.constants import Result, Status
from changes.testutils import APITestCase


class JobStepNeedsAbortTest(APITestCase):
    path = '/api/0/jobsteps/needs_abort/'

    def post(self, jobstep_ids, **kwargs):
        params = {'jobstep_ids': jobstep_ids}
        params.update(kwargs)
        return self.client.post(self.path, data=json.dumps(params), content_type='application/json')

    def test_none_needs_abort(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)

        jobstep = self.create_jobstep(jobphase)
        resp = self.post([jobstep.id.hex])
        assert resp.status_code == 200, resp
        assert self.unserialize(resp) == {'needs_abort': []}, resp.data

    def test_several_needs_abort(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)

        jobstep_ignored = self.create_jobstep(jobphase)
        jobstep_finished_ignored = self.create_jobstep(jobphase, status=Status.finished)
        jobstep1 = self.create_jobstep(jobphase, status=Status.finished, result=Result.aborted)
        jobstep2 = self.create_jobstep(jobphase, status=Status.finished, result=Result.failed, data={'timed_out': True})

        resp = self.post([step.id.hex for step in (jobstep_ignored, jobstep_finished_ignored, jobstep1, jobstep2)])

        assert resp.status_code == 200
        data = self.unserialize(resp)['needs_abort']
        assert len(data) == 2
        assert set(data) == {jobstep1.id.hex, jobstep2.id.hex}
