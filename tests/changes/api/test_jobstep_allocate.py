from __future__ import absolute_import

from mock import patch

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
        assert resp.data == '[]', resp.data

    @patch('changes.buildsteps.base.BuildStep.get_allocation_command',)
    def test_several_queued(self, mock_get_allocation_command):
        project = self.create_project()
        build = self.create_build(project, status=Status.pending_allocation)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        plan = self.create_plan()
        plan.projects.append(project)
        self.create_step(plan)
        self.create_job_plan(job, plan)

        jobstep_ignored = self.create_jobstep(jobphase, status=Status.unknown)
        jobstep_first_q = self.create_jobstep(jobphase, status=Status.pending_allocation)
        jobstep_second_q = self.create_jobstep(jobphase, status=Status.pending_allocation)

        mock_get_allocation_command.return_value = 'echo 1'

        # ensure we get back the latest queued jobstep first
        resp = self.client.post(self.path)

        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == jobstep_second_q.id.hex
        assert data[0]['status']['id'] == Status.allocated.name
        assert data[0]['resources']
        assert data[0]['cmd'] == 'echo 1'

        # ensure we get back the only other queued jobstep next
        resp = self.client.post(self.path)

        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == jobstep_first_q.id.hex
        assert data[0]['status']['id'] == Status.allocated.name
        assert data[0]['resources']
        assert data[0]['cmd'] == 'echo 1'

        # all queued!
        self.create_jobstep(jobphase, status=Status.unknown)
        resp = self.client.post(self.path)
        assert resp.status_code == 200
        assert resp.data == '[]', 'Expecting no content'
