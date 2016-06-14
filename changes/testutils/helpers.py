from contextlib import contextmanager
from flask import current_app
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


NOT_SET = object()


@contextmanager
def override_config(key, value):
    orig_value = current_app.config.get(key, NOT_SET)
    current_app.config[key] = value
    try:
        yield
    finally:
        if orig_value is NOT_SET:
            del current_app.config[key]
        else:
            current_app.config[key] = orig_value
