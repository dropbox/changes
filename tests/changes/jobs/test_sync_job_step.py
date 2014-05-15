from __future__ import absolute_import

import mock

from changes.config import db
from changes.constants import Result, Status
from changes.jobs.sync_job_step import sync_job_step
from changes.models import (
    ItemStat, JobStep, ProjectOption, Step, Task, FileCoverage
)
from changes.testutils import TestCase


class SyncJobStepTest(TestCase):
    @mock.patch('changes.config.queue.delay')
    @mock.patch.object(Step, 'get_implementation')
    def test_in_progress(self, get_implementation, queue_delay):
        implementation = mock.Mock()
        get_implementation.return_value = implementation

        def mark_in_progress(step):
            step.status = Status.in_progress

        build = self.create_build(project=self.project)
        job = self.create_job(build=build)

        plan = self.create_plan()
        self.create_step(plan, implementation='test', order=0)
        self.create_job_plan(job, plan)

        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase)
        task = self.create_task(
            parent_id=job.id,
            task_id=step.id,
            task_name='sync_job_step',
        )

        db.session.add(ItemStat(item_id=job.id, name='tests_missing', value=1))
        db.session.commit()

        implementation.update_step.side_effect = mark_in_progress

        sync_job_step(
            step_id=step.id.hex,
            task_id=step.id.hex,
            parent_task_id=job.id.hex,
        )

        get_implementation.assert_called_once_with()

        implementation.update_step.assert_called_once_with(
            step=step
        )

        db.session.expire(step)
        db.session.expire(task)

        step = JobStep.query.get(step.id)

        assert step.status == Status.in_progress

        task = Task.query.get(task.id)

        assert task.status == Status.in_progress

        queue_delay.assert_any_call('sync_job_step', kwargs={
            'step_id': step.id.hex,
            'task_id': step.id.hex,
            'parent_task_id': job.id.hex,
        }, countdown=5)

    @mock.patch('changes.config.queue.delay')
    @mock.patch.object(Step, 'get_implementation')
    def test_finished(self, get_implementation, queue_delay):
        implementation = mock.Mock()
        get_implementation.return_value = implementation

        def mark_finished(step):
            step.status = Status.finished
            step.result = Result.passed

        implementation.update_step.side_effect = mark_finished

        build = self.create_build(project=self.project)
        job = self.create_job(build=build)

        plan = self.create_plan()
        self.create_step(plan, implementation='test', order=0)
        self.create_job_plan(job, plan)

        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase)
        task = self.create_task(
            parent_id=job.id,
            task_id=step.id,
            task_name='sync_job_step',
            status=Status.finished,
        )

        db.session.add(FileCoverage(
            job=job, step=step, project=job.project,
            filename='foo.py', data='CCCUUUCCCUUNNN',
            lines_covered=6,
            lines_uncovered=5,
            diff_lines_covered=3,
            diff_lines_uncovered=2,
        ))
        db.session.commit()

        sync_job_step(
            step_id=step.id.hex,
            task_id=step.id.hex,
            parent_task_id=job.id.hex,
        )

        get_implementation.assert_called_once_with()

        implementation.update_step.assert_called_once_with(
            step=step
        )

        db.session.expire(step)
        db.session.expire(task)

        step = JobStep.query.get(step.id)

        assert step.status == Status.finished

        task = Task.query.get(task.id)

        assert task.status == Status.finished

        assert len(queue_delay.mock_calls) == 0

        stat = ItemStat.query.filter(
            ItemStat.item_id == step.id,
            ItemStat.name == 'tests_missing',
        ).first()
        assert stat.value == 0

        stat = ItemStat.query.filter(
            ItemStat.item_id == step.id,
            ItemStat.name == 'lines_covered',
        ).first()
        assert stat.value == 6

        stat = ItemStat.query.filter(
            ItemStat.item_id == step.id,
            ItemStat.name == 'lines_uncovered',
        ).first()
        assert stat.value == 5

        stat = ItemStat.query.filter(
            ItemStat.item_id == step.id,
            ItemStat.name == 'diff_lines_covered',
        ).first()
        assert stat.value == 3

        stat = ItemStat.query.filter(
            ItemStat.item_id == step.id,
            ItemStat.name == 'diff_lines_uncovered',
        ).first()
        assert stat.value == 2

    @mock.patch('changes.config.queue.delay')
    @mock.patch.object(Step, 'get_implementation')
    def test_missing_test_results_and_expected(self, get_implementation, queue_delay):
        implementation = mock.Mock()
        get_implementation.return_value = implementation

        def mark_finished(step):
            step.status = Status.finished
            step.result = Result.passed

        implementation.update_step.side_effect = mark_finished

        build = self.create_build(project=self.project)
        job = self.create_job(build=build)

        plan = self.create_plan()
        self.create_step(plan, implementation='test', order=0)
        self.create_job_plan(job, plan)

        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase)

        db.session.add(ProjectOption(
            project_id=self.project.id,
            name='build.expect-tests',
            value='1'
        ))
        db.session.commit()

        sync_job_step(
            step_id=step.id.hex,
            task_id=step.id.hex,
            parent_task_id=job.id.hex,
        )

        db.session.expire(step)

        step = JobStep.query.get(step.id)

        assert step.status == Status.finished
        assert step.result == Result.failed

        stat = ItemStat.query.filter(
            ItemStat.item_id == step.id,
            ItemStat.name == 'tests_missing',
        ).first()
        assert stat.value == 1
