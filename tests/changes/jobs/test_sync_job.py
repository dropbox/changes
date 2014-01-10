from __future__ import absolute_import

import mock

from changes.config import db
from changes.constants import Status
from changes.jobs.sync_job import sync_job
from changes.models import Job, Step, Build
from changes.testutils import TestCase


class SyncBuildTest(TestCase):
    @mock.patch('changes.jobs.sync_job.queue.delay')
    @mock.patch.object(Step, 'get_implementation')
    @mock.patch('changes.jobs.sync_job.publish_build_update')
    @mock.patch('changes.jobs.sync_job.publish_job_update')
    def test_in_progress(self, publish_job_update, publish_build_update,
                         get_implementation, queue_delay):
        implementation = mock.Mock()
        get_implementation.return_value = implementation

        build = self.create_build(project=self.project)
        job = self.create_job(build=build)

        plan = self.create_plan()
        self.create_step(plan, implementation='test', order=0)
        self.create_job_plan(job, plan)

        def mark_in_progress(job):
            job.status = Status.in_progress

        implementation.execute.side_effect = mark_in_progress

        sync_job(job_id=job.id.hex)

        get_implementation.assert_called_once_with()

        implementation.execute.assert_called_once_with(
            job=job,
        )

        db.session.expire(build)

        build = Build.query.get(build.id)

        assert build.status == Status.in_progress

        queue_delay.assert_any_call('sync_job', kwargs={
            'job_id': job.id.hex,
        }, countdown=5)

        publish_build_update.assert_called_once_with(build)
        publish_job_update.assert_called_once_with(job)

    @mock.patch('changes.jobs.sync_job.queue.delay')
    @mock.patch.object(Step, 'get_implementation')
    @mock.patch('changes.jobs.sync_job.publish_build_update')
    @mock.patch('changes.jobs.sync_job.publish_job_update')
    def test_finished(self, publish_job_update, publish_build_update,
                      get_implementation, queue_delay):
        implementation = mock.Mock()
        get_implementation.return_value = implementation

        def mark_finished(job):
            job.duration = 5000
            job.status = Status.finished

        implementation.execute.side_effect = mark_finished

        build = self.create_build(project=self.project)
        job = self.create_job(build=build)

        plan = self.create_plan()
        self.create_step(plan, implementation='test', order=0)
        self.create_job_plan(job, plan)

        sync_job(job_id=job.id.hex)

        db.session.expire(job)
        db.session.expire(build)

        job = Job.query.get(job.id)
        build = Build.query.get(build.id)

        assert job.status == Status.finished
        assert build.status == Status.finished

        publish_build_update.assert_called_once_with(build)
        publish_job_update.assert_called_once_with(job)

        queue_delay.assert_any_call('update_project_plan_stats', kwargs={
            'project_id': self.project.id.hex,
            'plan_id': plan.id.hex,
        }, countdown=1)

        queue_delay.assert_any_call('notify_listeners', kwargs={
            'job_id': job.id.hex,
            'signal_name': 'job.finished',
        })
