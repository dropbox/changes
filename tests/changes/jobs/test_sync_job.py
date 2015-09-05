from __future__ import absolute_import

from datetime import datetime
from flask import current_app
import mock

from changes.constants import Status, Result
from changes.config import db
from changes.jobs.sync_job import sync_job, _should_retry_jobstep, _find_and_retry_jobsteps
import changes.jobs.sync_job
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

        step2 = self.create_jobstep(self.jobphase, status=Status.finished,
                                    replacement_id=step.id)

        self.jobstep.status = Status.finished
        db.session.add(self.jobstep)

        db.session.add(ItemStat(item_id=step.id, name='tests_missing', value=1))
        db.session.add(ItemStat(item_id=step.id, name='lines_covered', value=10))
        db.session.add(ItemStat(item_id=step.id, name='lines_uncovered', value=25))
        # this shouldn't affect aggregated stats since this jobstep is replaced
        db.session.add(ItemStat(item_id=step2.id, name='lines_uncovered', value=10))
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

    def test_should_retry_jobstep(self):
        self.jobstep.result = Result.infra_failed
        assert _should_retry_jobstep(self.jobstep)

        # currently only retry infra failures
        self.jobstep.result = Result.failed
        assert not _should_retry_jobstep(self.jobstep)
        self.jobstep.result = Result.infra_failed

        # don't retry a jobstep that is already retried
        self.jobstep.replacement_id = 0
        assert not _should_retry_jobstep(self.jobstep)
        self.jobstep.replacement_id = None

        # don't retry jobstep that had too long of a duration
        ts = 10000
        changes.jobs.sync_job.MAX_DURATION_FOR_RETRY_SECS = 10
        self.jobstep.date_started = datetime.utcfromtimestamp(ts)
        self.jobstep.date_finished = datetime.utcfromtimestamp(ts + 11)
        assert not _should_retry_jobstep(self.jobstep)
        self.jobstep.date_started = self.jobstep.date_finished = None

        # don't retry a jobstep that has already been retried
        self.create_jobstep(self.jobphase, status=Status.finished,
                            replacement_id=self.jobstep.id)
        assert not _should_retry_jobstep(self.jobstep)

    @mock.patch('changes.jobs.sync_job._should_retry_jobstep')
    def test_find_and_retry_jobsteps(self, should_retry_jobstep):
        should_retry_jobstep.return_value = True
        implementation = mock.Mock()
        phase = self.job.phases[0]

        # test that it actually retries
        _find_and_retry_jobsteps(phase, implementation)
        implementation.create_replacement_jobstep.assert_called_once_with(self.jobstep)

        # test JOBSTEP_RETRY_MAX
        implementation.reset_mock()
        current_app.config['JOBSTEP_RETRY_MAX'] = 0
        _find_and_retry_jobsteps(phase, implementation)
        implementation.create_replacement_jobstep.assert_not_called()

        # test already_retried
        current_app.config['JOBSTEP_RETRY_MAX'] = 1
        self.create_jobstep(phase, status=Status.finished,
                            replacement_id=self.jobstep.id)
        _find_and_retry_jobsteps(phase, implementation)
        implementation.create_replacement_jobstep.assert_not_called()
