from __future__ import absolute_import

import json

import mock
from urllib import urlencode

from changes.testutils import APITestCase
from changes.buildsteps.base import BuildStep
from changes.constants import Status
from changes.ext.redis import UnableToGetLock


class JobStepAllocateTestNew(APITestCase):
    path = '/api/0/jobsteps/allocate/'

    def post(self, jobstep_ids, **kwargs):
        params = {'jobstep_ids': jobstep_ids}
        params.update(kwargs)
        return self.client.post(self.path, data=json.dumps(params), content_type='application/json')

    def assert_successful_allocate(self, jobstep_ids, cluster=None):
        resp = self.post(jobstep_ids, cluster=cluster)
        assert resp.status_code == 200, resp
        assert sorted(self.unserialize(resp)['allocated']) == sorted(jobstep_ids)

    def get(self, **kwargs):
        query_string = '?' + urlencode(kwargs) if kwargs else ''
        return self.client.get(self.path + query_string)

    def test_none_queued(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)

        self.create_jobstep(jobphase, status=Status.unknown)
        resp = self.get()
        assert resp.status_code == 200, resp
        assert self.unserialize(resp) == {'jobsteps': []}, resp.data

    def test_simple_alloc(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase, status=Status.pending_allocation)

        self.assert_successful_allocate([jobstep.id.hex])

    @mock.patch('changes.config.redis.lock',)
    def test_locked(self, mock_allocate):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)

        jobstep = self.create_jobstep(jobphase, status=Status.unknown)

        mock_allocate.side_effect = UnableToGetLock("Can't get lock")
        resp = self.post([jobstep.id.hex])
        assert resp.status_code == 409

    def test_already_allocated(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)

        jobstep_pending = self.create_jobstep(jobphase, status=Status.pending_allocation)
        jobstep_allocated = self.create_jobstep(jobphase, status=Status.allocated)

        resp = self.post([jobstep_pending.id.hex, jobstep_allocated.id.hex])
        assert resp.status_code == 409
        assert jobstep_allocated.status == Status.allocated
        # allocation should be all or nothing
        assert jobstep_pending.status == Status.pending_allocation

    @mock.patch('changes.models.JobPlan.get_build_step_for_job')
    def test_several_queued(self, get_build_step_for_job):
        jobphases = []
        jobid2buildstep = {}
        get_build_step_for_job.side_effect = lambda jobid: jobid2buildstep[jobid]
        # use multiple projects/jobs/jobphases to keep things interesting
        # (tests our memoization)
        for i in xrange(2):
            project = self.create_project()
            build = self.create_build(project, status=Status.pending_allocation)
            job = self.create_job(build)
            jobphase = self.create_jobphase(job)
            plan = self.create_plan(project)
            self.create_step(plan)
            jobplan = self.create_job_plan(job, plan)
            implementation = mock.Mock(spec=BuildStep)
            implementation.get_resource_limits.return_value = {}
            implementation.get_allocation_command.return_value = 'echo %d' % i
            jobid2buildstep[job.id] = (jobplan, implementation)
            jobphases.append(jobphase)

        jobstep_ignored = self.create_jobstep(jobphases[0], status=Status.unknown)
        jobstep_first_q = self.create_jobstep(jobphases[0], status=Status.pending_allocation)
        jobstep_second_q = self.create_jobstep(jobphases[1], status=Status.pending_allocation)
        jobstep_third_q = self.create_jobstep(jobphases[1], status=Status.pending_allocation)

        # ensure we get back the earliest queued jobsteps first
        resp = self.get(limit=2)

        assert resp.status_code == 200
        data = self.unserialize(resp)['jobsteps']
        assert len(data) == 2
        assert data[0]['id'] == jobstep_first_q.id.hex
        assert data[0]['status']['id'] == Status.pending_allocation.name
        assert data[0]['resources']
        assert data[0]['cmd'] == 'echo 0'
        assert data[1]['id'] == jobstep_second_q.id.hex
        assert data[1]['status']['id'] == Status.pending_allocation.name
        assert data[1]['resources']
        assert data[1]['cmd'] == 'echo 1'

        self.assert_successful_allocate([data[0]['id'], data[1]['id']])

        # ensure we get back the only other queued jobstep next
        resp = self.get()

        assert resp.status_code == 200
        data = self.unserialize(resp)['jobsteps']
        assert len(data) == 1
        assert data[0]['id'] == jobstep_third_q.id.hex
        assert data[0]['status']['id'] == Status.pending_allocation.name
        assert data[0]['resources']
        assert data[0]['cmd'] == 'echo 1'

        self.assert_successful_allocate([data[0]['id']])

        # all queued!
        self.create_jobstep(jobphase, status=Status.unknown)
        resp = self.get()
        assert resp.status_code == 200
        assert self.unserialize(resp) == {'jobsteps': []}, 'Expecting no content'

    def test_none_queued_for_cluster(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)

        self.create_jobstep(jobphase, status=Status.pending_allocation)

        resp = self.get(cluster='foo')
        assert resp.status_code == 200, resp
        assert self.unserialize(resp) == {'jobsteps': []}, resp.data

    def test_only_cluster_queued(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)

        self.create_jobstep(jobphase, status=Status.pending_allocation, cluster='foo')

        resp = self.get()
        assert resp.status_code == 200, resp
        assert self.unserialize(resp) == {'jobsteps': []}, resp.data

    @mock.patch('changes.buildsteps.base.BuildStep.get_allocation_command',)
    def test_several_queued_cluster(self, mock_get_allocation_command):
        project = self.create_project()
        build = self.create_build(project, status=Status.pending_allocation)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        plan = self.create_plan(project)
        self.create_step(plan)
        self.create_job_plan(job, plan)

        other_cluster_job = self.create_job(build)
        other_cluster_jobphase = self.create_jobphase(other_cluster_job)
        other_cluster_jobstep = self.create_jobstep(other_cluster_jobphase, status=Status.pending_allocation,
                                                    cluster='bar', label='other')
        other_cluster_plan = self.create_plan(project)
        self.create_step(other_cluster_plan)
        self.create_job_plan(other_cluster_job, other_cluster_plan)

        jobstep_ignored = self.create_jobstep(jobphase, status=Status.unknown, cluster='foo')
        jobstep_first_q = self.create_jobstep(jobphase, status=Status.pending_allocation, cluster='foo', label='first')
        jobstep_second_q = self.create_jobstep(jobphase, status=Status.pending_allocation, cluster='foo', label='second')
        jobstep_third_q = self.create_jobstep(jobphase, status=Status.pending_allocation, cluster='foo', label='third')

        mock_get_allocation_command.return_value = 'echo 1'

        # ensure we get back the earliest queued jobsteps first
        resp = self.get(cluster='foo', limit=2)

        assert resp.status_code == 200
        data = self.unserialize(resp)['jobsteps']
        assert len(data) == 2
        assert data[0]['id'] == jobstep_first_q.id.hex
        assert data[1]['id'] == jobstep_second_q.id.hex

        self.assert_successful_allocate([data[0]['id'], data[1]['id']], cluster='foo')

        # ensure we get back the only other queued jobstep next
        resp = self.get(cluster='foo')

        assert resp.status_code == 200
        data = self.unserialize(resp)['jobsteps']
        assert len(data) == 1
        assert data[0]['id'] == jobstep_third_q.id.hex

        self.assert_successful_allocate([data[0]['id']], cluster='foo')

        # all queued!
        self.create_jobstep(jobphase, status=Status.unknown)
        resp = self.get(cluster='foo')
        assert resp.status_code == 200
        assert self.unserialize(resp) == {'jobsteps': []}, resp.data


# TODO(nate): remove these tests when we migrate to the new method
class JobStepAllocateTest(APITestCase):
    path = '/api/0/jobsteps/allocate/'

    params = {
        'resources': {
            'cpus': '8',
            'mem': '16384',
        },
    }

    def post_simple(self, **kwargs):
        params = self.params.copy()
        params.update(kwargs)
        return self.client.post(self.path, data=json.dumps(params), content_type='application/json')

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

    @mock.patch('changes.config.redis.lock',)
    def test_cant_allocate(self, mock_allocate):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)

        self.create_jobstep(jobphase, status=Status.unknown)

        mock_allocate.side_effect = UnableToGetLock("Can't get lock")
        resp = self.post_simple()
        assert resp.status_code == 503

    @mock.patch('changes.buildsteps.base.BuildStep.get_allocation_command',)
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

    def test_none_queued_for_cluster(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)

        self.create_jobstep(jobphase, status=Status.pending_allocation)

        resp = self.post_simple(cluster='foo')
        assert resp.status_code == 200, resp
        assert resp.data == '[]', resp.data

    def test_only_cluster_queued(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)

        self.create_jobstep(jobphase, status=Status.pending_allocation, cluster='foo')

        resp = self.post_simple()
        assert resp.status_code == 200, resp
        assert resp.data == '[]', resp.data

    @mock.patch('changes.buildsteps.base.BuildStep.get_allocation_command',)
    def test_several_queued_cluster(self, mock_get_allocation_command):
        project = self.create_project()
        build = self.create_build(project, status=Status.pending_allocation)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        plan = self.create_plan(project)
        self.create_step(plan)
        self.create_job_plan(job, plan)

        other_cluster_job = self.create_job(build)
        other_cluster_jobphase = self.create_jobphase(other_cluster_job)
        other_cluster_jobstep = self.create_jobstep(other_cluster_jobphase, status=Status.pending_allocation,
                                                    cluster='bar', label='other')
        other_cluster_plan = self.create_plan(project)
        self.create_step(other_cluster_plan)
        self.create_job_plan(other_cluster_job, other_cluster_plan)

        jobstep_ignored = self.create_jobstep(jobphase, status=Status.unknown, cluster='foo')
        jobstep_first_q = self.create_jobstep(jobphase, status=Status.pending_allocation, cluster='foo', label='first')
        jobstep_second_q = self.create_jobstep(jobphase, status=Status.pending_allocation, cluster='foo', label='second')
        jobstep_third_q = self.create_jobstep(jobphase, status=Status.pending_allocation, cluster='foo', label='third')

        mock_get_allocation_command.return_value = 'echo 1'

        # ensure we get back the earliest queued jobsteps first
        resp = self.post_simple(cluster='foo')

        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == jobstep_first_q.id.hex
        assert data[1]['id'] == jobstep_second_q.id.hex

        # ensure we get back the only other queued jobstep next
        resp = self.post_simple(cluster='foo')

        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == jobstep_third_q.id.hex

        # all queued!
        self.create_jobstep(jobphase, status=Status.unknown)
        resp = self.post_simple(cluster='foo')
        assert resp.status_code == 200
        assert resp.data == '[]', 'Expecting no content'

    @mock.patch('changes.buildsteps.base.BuildStep.get_allocation_command',)
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

        with mock.patch('changes.buildsteps.base.BuildStep.get_resource_limits') as get_limits:
            get_limits.return_value = {'memory': 8192, 'cpus': 4}  # too expensive for params.
            resp = self.client.post(self.path, data=params, content_type='application/json')

        assert resp.status_code == 200, resp.data
        assert self.unserialize(resp) == []

        with mock.patch('changes.buildsteps.base.BuildStep.get_resource_limits') as get_limits:
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
