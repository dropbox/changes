from __future__ import absolute_import

from datetime import datetime, timedelta

from changes.config import queue, statsreporter
from changes.constants import Status
from changes.models.task import Task
from changes.queue.task import TrackedTask

CHECK_TIME = timedelta(minutes=60)
EXPIRE_TIME = timedelta(days=7)


# NOTE: This isn't itself a TrackedTask, but probably should be.
@statsreporter.timer('task_duration_cleanup_task')
def cleanup_tasks():
    """
    Find any tasks which haven't checked in within a reasonable time period and
    requeue them if necessary.

    Additionally remove any old Task entries which are completed.
    """
    now = datetime.utcnow()

    pending_tasks = Task.query.filter(
        Task.status != Status.finished,
        Task.date_modified < now - CHECK_TIME,
    )

    for task in pending_tasks:
        task_func = TrackedTask(queue.get_task(task.task_name))
        task_func.delay(
            task_id=task.task_id.hex,
            parent_task_id=task.parent_id.hex if task.parent_id else None,
            **task.data['kwargs']
        )

    deleted = Task.query.filter(
        Task.status == Status.finished,
        Task.date_modified < now - EXPIRE_TIME,
        # Filtering by date_created isn't necessary, but it allows us to filter using an index on
        # a value that doesn't update, which makes our deletion more efficient.
        Task.date_created < now - EXPIRE_TIME,
    ).delete(synchronize_session=False)
    statsreporter.stats().incr('tasks_deleted', deleted)
