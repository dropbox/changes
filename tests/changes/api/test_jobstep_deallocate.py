from uuid import uuid4

from changes.testutils import APITestCase
from changes.constants import Status


class JobStepDeallocateTest(APITestCase):
    path_tmpl = '/api/0/jobsteps/{0}/deallocate/'

    def test_no_jobstep(self):
        path = self.path_tmpl.format(uuid4())
        resp = self.client.post(path)
        assert resp.status_code == 404, resp

    def test_not_allocated(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase, status=Status.unknown)

        path = self.path_tmpl.format(jobstep.id.hex)
        resp = self.client.post(path)
        assert resp.status_code == 400
        data = self.unserialize(resp)
        assert data['actual_status'] == Status.unknown.name

    def test_deallocation(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase, status=Status.allocated)

        path = self.path_tmpl.format(jobstep.id.hex)
        resp = self.client.post(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == jobstep.id.hex
        assert data['status']['id'] == 'pending_allocation'

        resp = self.client.post(path)
        assert resp.status_code == 400, resp
        data = self.unserialize(resp)
        assert data['actual_status'] == 'pending_allocation'
