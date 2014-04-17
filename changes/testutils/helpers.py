from functools import wraps
from mock import patch

from changes.config import queue
from changes.queue.task import TooManyRetries


def eager_tasks(func):
    @wraps(func)
    # prevent retries due to recursion issues
    def wrapped(*args, **kwargs):
        with patch('changes.queue.task.TrackedTask._retry', side_effect=TooManyRetries()):
            queue.celery.conf.CELERY_ALWAYS_EAGER = True
            try:
                return func(*args, **kwargs)
            finally:
                queue.celery.conf.CELERY_ALWAYS_EAGER = False
    return wrapped
