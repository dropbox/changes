from changes.testutils import APITestCase
from changes.constants import Status


class JobStepAllocateTest(APITestCase):
    path = '/api/0/jobsteps/allocate/'

    def test_none_queued(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)

        # empty logs
        self.create_jobstep(jobphase, status=Status.unknown)
        resp = self.client.post(self.path)
        assert resp.status_code == 200, resp
        assert resp.data == '""', resp.data

    def test_several_queued(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)

        jobstep_ignored = self.create_jobstep(jobphase, status=Status.unknown)
        jobstep_first_q = self.create_jobstep(jobphase, status=Status.queued)
        jobstep_second_q = self.create_jobstep(jobphase, status=Status.queued)

        # ensure we get back the latest queued jobstep first
        resp = self.client.post(self.path)

        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == jobstep_second_q.id.hex
        assert data['status']['id'] == Status.allocated.name

        # ensure we get back the only other queued jobstep next
        resp = self.client.post(self.path)

        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == jobstep_first_q.id.hex
        assert data['status']['id'] == Status.allocated.name

        # all queued!
        self.create_jobstep(jobphase, status=Status.unknown)
        resp = self.client.post(self.path)
        assert resp.status_code == 200
        assert resp.data == '""', 'Expecting no content'
