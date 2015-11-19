from __future__ import absolute_import

import json

from mock import patch

from changes.testutils import APITestCase
from changes.constants import Status
from changes.ext.redis import UnableToGetLock


class JobStepAllocateTest(APITestCase):
    path = '/api/0/jobsteps/allocate/'

    params = json.dumps({
        'resources': {
            'cpus': '8',
            'mem': '16384',
        },
    })

    def post_simple(self):
        return self.client.post(self.path, data=self.params, content_type='application/json')

    def test_none_queued(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)

        # empty logs
        self.create_jobstep(jobphase, status=Status.unknown)
        resp = self.post_simple()
        assert resp.status_code == 200, resp
        assert resp.data == '[]', resp.data

    @patch('changes.config.redis.lock',)
    def test_cant_allocate(self, mock_allocate):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)

        self.create_jobstep(jobphase, status=Status.unknown)

        mock_allocate.side_effect = UnableToGetLock("Can't get lock")
        resp = self.post_simple()
        assert resp.status_code == 503

    @patch('changes.buildsteps.base.BuildStep.get_allocation_command',)
    def test_several_queued(self, mock_get_allocation_command):
        project = self.create_project()
        build = self.create_build(project, status=Status.pending_allocation)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        plan = self.create_plan(project)
        self.create_step(plan)
        self.create_job_plan(job, plan)

        jobstep_ignored = self.create_jobstep(jobphase, status=Status.unknown)
        jobstep_first_q = self.create_jobstep(jobphase, status=Status.pending_allocation)
        jobstep_second_q = self.create_jobstep(jobphase, status=Status.pending_allocation)
        jobstep_third_q = self.create_jobstep(jobphase, status=Status.pending_allocation)

        mock_get_allocation_command.return_value = 'echo 1'

        # ensure we get back the earliest queued jobsteps first
        resp = self.post_simple()

        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == jobstep_first_q.id.hex
        assert data[0]['status']['id'] == Status.allocated.name
        assert data[0]['resources']
        assert data[0]['cmd'] == 'echo 1'
        assert data[1]['id'] == jobstep_second_q.id.hex
        assert data[1]['status']['id'] == Status.allocated.name
        assert data[1]['resources']
        assert data[1]['cmd'] == 'echo 1'

        # ensure we get back the only other queued jobstep next
        resp = self.post_simple()

        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == jobstep_third_q.id.hex
        assert data[0]['status']['id'] == Status.allocated.name
        assert data[0]['resources']
        assert data[0]['cmd'] == 'echo 1'

        # all queued!
        self.create_jobstep(jobphase, status=Status.unknown)
        resp = self.post_simple()
        assert resp.status_code == 200
        assert resp.data == '[]', 'Expecting no content'

    @patch('changes.buildsteps.base.BuildStep.get_allocation_command',)
    def test_limits_too_high(self, mock_get_allocation_command):
        mock_get_allocation_command.return_value = 'echo 1'

        project = self.create_project()
        build = self.create_build(project, status=Status.pending_allocation)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        plan = self.create_plan(project)
        self.create_step(plan)
        self.create_job_plan(job, plan)

        jobstep = self.create_jobstep(jobphase, status=Status.pending_allocation)

        params = json.dumps({
            'resources': {
                'cpus': '2',
                'mem': '8192',
            },
        })

        with patch('changes.buildsteps.base.BuildStep.get_resource_limits') as get_limits:
            get_limits.return_value = {'memory': 8192, 'cpus': 4}  # too expensive for params.
            resp = self.client.post(self.path, data=params, content_type='application/json')

        assert resp.status_code == 200, resp.data
        assert self.unserialize(resp) == []

        with patch('changes.buildsteps.base.BuildStep.get_resource_limits') as get_limits:
            get_limits.return_value = {'memory': 8192, 'cpus': 1}  # now we're cheap enough.
            resp = self.client.post(self.path, data=params, content_type='application/json')

        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == jobstep.id.hex
        assert data[0]['status']['id'] == Status.allocated.name
        assert data[0]['resources']
        assert data[0]['resources']['cpus'] == 1
        assert data[0]['resources']['mem'] == 8192
        assert data[0]['cmd'] == 'echo 1'
