from __future__ import absolute_import

from mock import patch

from datetime import datetime
from uuid import uuid4

from changes.constants import Status
from changes.jobs.cleanup_tasks import cleanup_tasks, CHECK_TIME
from changes.models import Task
from changes.testutils import TestCase


class CleanupTasksTest(TestCase):
    @patch('changes.config.queue.delay')
    def test_queues_jobs(self, mock_delay):
        now = datetime.utcnow()
        old_dt = now - (CHECK_TIME * 2)

        task = self.create_task(
            task_name='cleanup_tasks',
            task_id=uuid4(),
            date_created=old_dt,
            status=Status.queued,
            data={'kwargs': {'foo': 'bar'}},
        )

        self.create_task(
            task_name='cleanup_tasks',
            task_id=uuid4(),
            date_created=now,
            status=Status.finished,
        )

        self.create_task(
            task_name='cleanup_tasks',
            task_id=uuid4(),
            date_created=old_dt,
            status=Status.finished,
        )

        cleanup_tasks()

        mock_delay.assert_called_once_with(
            'cleanup_tasks',
            countdown=5,
            kwargs={
                'task_id': task.task_id.hex,
                'parent_task_id': None,
                'foo': 'bar',
            },
        )

        task = Task.query.get(task.id)

        assert task.date_modified > old_dt
