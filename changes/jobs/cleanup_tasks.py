from __future__ import absolute_import

from datetime import datetime, timedelta

from changes.config import queue
from changes.constants import Status
from changes.models import Task
from changes.queue.task import TrackedTask, tracked_task

CHECK_TIME = timedelta(minutes=5)


@tracked_task
def cleanup_tasks():
    """
    Find any tasks which haven't checked in within a reasonable time period and
    requeue them if nescessary.
    """
    now = datetime.utcnow()
    cutoff = now - CHECK_TIME

    pending_tasks = Task.query.filter(
        Task.status != Status.finished,
        Task.date_modified < cutoff,
    )

    for task in pending_tasks:
        task_func = TrackedTask(queue.get_task(task.task_name))
        task_func.delay(
            task_id=task.task_id.hex,
            parent_task_id=task.parent_id.hex if task.parent_id else None,
            **task.data['kwargs']
        )
