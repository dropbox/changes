from __future__ import absolute_import

from datetime import timedelta

from changes.queue.task import TrackedTask, tracked_task

CHECK_TIME = timedelta(minutes=60)


@tracked_task
def cleanup_tasks():
    pass