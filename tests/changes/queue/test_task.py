from __future__ import absolute_import

import mock

from uuid import UUID

from changes.config import db
from changes.constants import Status
from changes.models import Task
from changes.testutils import TestCase
from changes.queue.task import tracked_task


@tracked_task
def success_task(foo='bar'):
    pass


@tracked_task
def unfinished_task(foo='bar'):
    raise unfinished_task.NotFinished


@tracked_task
def error_task(foo='bar'):
    raise Exception


class DelayTest(TestCase):
    @mock.patch('changes.config.queue.delay')
    def test_simple(self, queue_delay):
        task_id = UUID('33846695b2774b29a71795a009e8168a')
        parent_task_id = UUID('659974858dcf4aa08e73a940e1066328')
        success_task.delay(
            foo='bar',
            task_id=task_id.hex,
            parent_task_id=parent_task_id.hex,
        )

        queue_delay.assert_called_once_with('success_task', kwargs={
            'foo': 'bar',
            'task_id': task_id.hex,
            'parent_task_id': parent_task_id.hex,
        }, countdown=5)

        task = Task.query.filter(
            Task.task_id == task_id,
            Task.task_name == 'success_task'
        ).first()

        assert task
        assert task.status == Status.queued
        assert task.parent_id == parent_task_id
        assert task.data == {
            'kwargs': {'foo': 'bar'},
        }


class DelayIfNeededTest(TestCase):
    @mock.patch('changes.config.queue.delay')
    def test_task_doesnt_exist(self, queue_delay):
        task_id = UUID('33846695b2774b29a71795a009e8168a')
        parent_task_id = UUID('659974858dcf4aa08e73a940e1066328')
        success_task.delay_if_needed(
            foo='bar',
            task_id=task_id.hex,
            parent_task_id=parent_task_id.hex,
        )

        queue_delay.assert_called_once_with('success_task', kwargs={
            'foo': 'bar',
            'task_id': task_id.hex,
            'parent_task_id': parent_task_id.hex,
        }, countdown=5)

        task = Task.query.filter(
            Task.task_id == task_id,
            Task.task_name == 'success_task'
        ).first()

        assert task
        assert task.status == Status.queued
        assert task.parent_id == parent_task_id
        assert task.data == {
            'kwargs': {'foo': 'bar'},
        }

    @mock.patch('changes.queue.task.needs_requeued', mock.Mock(return_value=False))
    @mock.patch('changes.config.queue.delay')
    def test_task_does_exist_but_not_outdated(self, queue_delay):
        task_id = UUID('33846695b2774b29a71795a009e8168a')
        parent_task_id = UUID('659974858dcf4aa08e73a940e1066328')

        self.create_task(
            task_name='success_task',
            task_id=task_id,
            parent_id=parent_task_id,
            status=Status.in_progress,
        )

        success_task.delay_if_needed(
            foo='bar',
            task_id=task_id.hex,
            parent_task_id=parent_task_id.hex,
        )

        assert queue_delay.called is False

    @mock.patch('changes.queue.task.needs_requeued', mock.Mock(return_value=True))
    @mock.patch('changes.config.queue.delay')
    def test_task_does_exist_and_needs_run(self, queue_delay):
        task_id = UUID('33846695b2774b29a71795a009e8168a')
        parent_task_id = UUID('659974858dcf4aa08e73a940e1066328')

        self.create_task(
            task_name='success_task',
            task_id=task_id,
            parent_id=parent_task_id,
            status=Status.in_progress,

        )

        success_task.delay_if_needed(
            foo='bar',
            task_id=task_id.hex,
            parent_task_id=parent_task_id.hex,
        )

        queue_delay.assert_called_once_with('success_task', kwargs={
            'foo': 'bar',
            'task_id': task_id.hex,
            'parent_task_id': parent_task_id.hex,
        }, countdown=5)


class VerifyAllChildrenTest(TestCase):
    def test_children_unfinished(self):
        parent_task_id = UUID('659974858dcf4aa08e73a940e1066328')

        self.create_task(
            task_name='success_task',
            task_id=UUID('33846695b2774b29a71795a009e8168a'),
            parent_id=parent_task_id,
            status=Status.in_progress,
        )
        self.create_task(
            task_name='success_task',
            task_id=UUID('70e090f5c41e4175a9fd630464804bb0'),
            parent_id=parent_task_id,
            status=Status.finished,
        )

        success_task.task_id = parent_task_id.hex

        result = success_task.verify_all_children()
        assert result == Status.in_progress

    def test_children_finished(self):
        child_id = UUID('33846695b2774b29a71795a009e8168a')
        parent_task_id = UUID('659974858dcf4aa08e73a940e1066328')

        self.create_task(
            task_name='success_task',
            task_id=child_id,
            parent_id=parent_task_id,
            status=Status.finished,
        )

        success_task.task_id = parent_task_id.hex

        result = success_task.verify_all_children()
        assert result == Status.finished


class VerifyChildrenTest(TestCase):
    @mock.patch('changes.config.queue.delay')
    def test_missing_children(self, queue_delay):
        child_id = UUID('33846695b2774b29a71795a009e8168a')
        parent_task_id = UUID('659974858dcf4aa08e73a940e1066328')

        success_task.task_id = parent_task_id.hex

        result = success_task.verify_children(
            'unfinished_task', [child_id.hex]
        )
        assert result == Status.in_progress

        task = Task.query.filter(
            Task.task_id == child_id,
            Task.task_name == 'unfinished_task',
        ).first()

        assert task
        assert task.parent_id == parent_task_id

        queue_delay.assert_called_once_with('unfinished_task', kwargs={
            'task_id': child_id.hex,
            'parent_task_id': parent_task_id.hex,
        })

    def test_children_finished(self):
        child_id = UUID('33846695b2774b29a71795a009e8168a')
        parent_task_id = UUID('659974858dcf4aa08e73a940e1066328')

        self.create_task(
            task_name='success_task',
            task_id=child_id,
            parent_id=parent_task_id,
            status=Status.finished,
        )

        success_task.task_id = parent_task_id.hex

        result = success_task.verify_children(
            'success_task', [child_id.hex]
        )
        assert result == Status.finished


class RunTest(TestCase):
    @mock.patch('changes.config.queue.delay')
    @mock.patch('changes.config.queue.retry')
    def test_success(self, queue_retry, queue_delay):
        task_id = UUID('33846695b2774b29a71795a009e8168a')
        parent_task_id = UUID('659974858dcf4aa08e73a940e1066328')

        self.create_task(
            task_name='success_task',
            task_id=task_id,
            parent_id=parent_task_id,
        )

        success_task(
            foo='bar',
            task_id=task_id.hex,
            parent_task_id=parent_task_id.hex,
        )

        task = Task.query.filter(
            Task.task_id == task_id,
            Task.task_name == 'success_task'
        ).first()

        assert task
        assert task.status == Status.finished
        assert task.parent_id == parent_task_id

    @mock.patch('changes.config.queue.delay')
    @mock.patch('changes.config.queue.retry')
    def test_unfinished(self, queue_retry, queue_delay):
        task_id = UUID('33846695b2774b29a71795a009e8168a')
        parent_task_id = UUID('659974858dcf4aa08e73a940e1066328')

        self.create_task(
            task_name='unfinished_task',
            task_id=task_id,
            parent_id=parent_task_id,
        )

        unfinished_task(
            foo='bar',
            task_id=task_id.hex,
            parent_task_id=parent_task_id.hex,
        )

        task = Task.query.filter(
            Task.task_id == task_id,
            Task.task_name == 'unfinished_task'
        ).first()

        assert task
        assert task.status == Status.in_progress
        assert task.parent_id == parent_task_id

        queue_delay.assert_called_once_with(
            'unfinished_task',
            kwargs={
                'foo': 'bar',
                'task_id': task_id.hex,
                'parent_task_id': parent_task_id.hex,
            },
            countdown=5,
        )

    @mock.patch('changes.config.queue.delay')
    @mock.patch('changes.config.queue.retry')
    def test_error(self, queue_retry, queue_delay):
        task_id = UUID('33846695b2774b29a71795a009e8168a')
        parent_task_id = UUID('659974858dcf4aa08e73a940e1066328')

        self.create_task(
            task_name='error_task',
            task_id=task_id,
            parent_id=parent_task_id,
        )

        # force a commit as the error will cause a rollback
        db.session.commit()

        error_task(
            foo='bar',
            task_id=task_id.hex,
            parent_task_id=parent_task_id.hex,
        )

        task = Task.query.filter(
            Task.task_id == task_id,
            Task.task_name == 'error_task'
        ).first()

        assert task
        assert task.status == Status.in_progress
        assert task.num_retries == 1
        assert task.parent_id == parent_task_id

        queue_delay.assert_called_once_with(
            'error_task',
            kwargs={
                'foo': 'bar',
                'task_id': task_id.hex,
                'parent_task_id': parent_task_id.hex,
            },
            countdown=60,
        )
