from __future__ import absolute_import

import mock

from changes.constants import Status
from changes.config import db
from changes.jobs.sync_job import sync_job
from changes.models import ItemStat, Job, HistoricalImmutableStep, Task
from changes.testutils import TestCase


class SyncJobTest(TestCase):
    def setUp(self):
        super(SyncJobTest, self).setUp()
        self.project = self.create_project()
        self.build = self.create_build(project=self.project)
        self.job = self.create_job(build=self.build)
        self.jobphase = self.create_jobphase(self.job)
        self.jobstep = self.create_jobstep(self.jobphase)

        self.task = self.create_task(
            parent_id=self.build.id,
            task_id=self.job.id,
            task_name='sync_job',
        )

        self.plan = self.create_plan(self.project)
        self.step = self.create_step(self.plan, implementation='test', order=0)
        self.jobplan = self.create_job_plan(self.job, self.plan)

    @mock.patch('changes.jobs.sync_job.queue.delay')
    @mock.patch.object(HistoricalImmutableStep, 'get_implementation')
    def test_in_progress(self, get_implementation,
                         queue_delay):
        implementation = mock.Mock()
        get_implementation.return_value = implementation

        build, job, task = self.build, self.job, self.task

        self.create_task(
            task_name='sync_job_step',
            task_id=job.phases[0].steps[0].id,
            parent_id=job.id,
            status=Status.in_progress,
        )

        def mark_in_progress(job):
            job.status = Status.in_progress

        implementation.update.side_effect = mark_in_progress

        sync_job(
            job_id=job.id.hex,
            task_id=job.id.hex,
            parent_task_id=build.id.hex
        )

        get_implementation.assert_called_once_with()

        implementation.update.assert_called_once_with(
            job=self.job,
        )

        assert implementation.validate_phase.call_count == 0
        assert implementation.validate.call_count == 0

        queue_delay.assert_any_call('sync_job', kwargs={
            'job_id': job.id.hex,
            'task_id': job.id.hex,
            'parent_task_id': build.id.hex,
        }, countdown=5)

        task = Task.query.get(task.id)

        assert task.status == Status.in_progress

    @mock.patch('changes.jobs.sync_job.fire_signal')
    @mock.patch('changes.jobs.sync_job.queue.delay')
    @mock.patch.object(HistoricalImmutableStep, 'get_implementation')
    def test_finished(self, get_implementation, queue_delay,
                      mock_fire_signal):
        implementation = mock.Mock()
        get_implementation.return_value = implementation

        assert self.jobplan

        build, job, task = self.build, self.job, self.task

        step = job.phases[0].steps[0]

        self.create_task(
            task_name='sync_job_step',
            task_id=step.id,
            parent_id=job.id,
            status=Status.finished,
        )
        self.create_test(job)
        self.create_test(job)

        self.jobstep.status = Status.finished
        db.session.add(self.jobstep)

        db.session.add(ItemStat(item_id=step.id, name='tests_missing', value=1))
        db.session.add(ItemStat(item_id=step.id, name='lines_covered', value=10))
        db.session.add(ItemStat(item_id=step.id, name='lines_uncovered', value=25))
        db.session.commit()

        sync_job(
            job_id=job.id.hex,
            task_id=job.id.hex,
            parent_task_id=build.id.hex,
        )

        implementation.validate_phase.assert_called_once_with(phase=self.job.phases[0])
        implementation.validate.assert_called_once_with(job=self.job)

        job = Job.query.get(job.id)

        assert job.status == Status.finished

        queue_delay.assert_any_call('update_project_plan_stats', kwargs={
            'project_id': self.project.id.hex,
            'plan_id': self.plan.id.hex,
        }, countdown=1)

        mock_fire_signal.delay.assert_any_call(
            signal='job.finished',
            kwargs={'job_id': job.id.hex},
        )

        task = Task.query.get(task.id)

        assert task.status == Status.finished

        stat = ItemStat.query.filter(
            ItemStat.item_id == job.id,
            ItemStat.name == 'tests_missing',
        ).first()
        assert stat.value == 1

        stat = ItemStat.query.filter(
            ItemStat.item_id == job.id,
            ItemStat.name == 'lines_covered',
        ).first()
        assert stat.value == 10

        stat = ItemStat.query.filter(
            ItemStat.item_id == job.id,
            ItemStat.name == 'lines_uncovered',
        ).first()
        assert stat.value == 25
