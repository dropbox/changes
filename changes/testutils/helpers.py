from changes.config import queue
from functools import wraps


def eager_tasks(func):
    @wraps(func)
    def wrapped(*args, **kwargs):
        queue.celery.CELERY_ALWAYS_EAGER = True
        try:
            return func(*args, **kwargs)
        finally:
            queue.celery.CELERY_ALWAYS_EAGER = False
    return wrapped
