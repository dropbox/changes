from __future__ import absolute_import

from celery import Celery as CeleryApp

from .container import Container


class _Celery(object):
    def __init__(self, app, options):
        celery = CeleryApp(app.import_name, broker=app.config['CELERY_BROKER_URL'])
        celery.conf.update(app.config)
        TaskBase = celery.Task

        class ContextTask(TaskBase):
            abstract = True

            def __call__(self, *args, **kwargs):
                with app.app_context():
                    return TaskBase.__call__(self, *args, **kwargs)

        celery.Task = ContextTask

        self.app = app
        self.celery = celery
        self.tasks = {}

    def delay(self, name, *args, **kwargs):
        # We don't assume the task is registered at this point, so manually
        # publish it
        with self.celery.producer_or_acquire() as P:
            task_id = P.publish_task(name, args, kwargs)
        return task_id

    def retry(self, name, args, kwargs, **options):
        # unlike delay, we actually want to rely on Celery's retry logic
        # and because we can only execute this within a task, it's safe
        # to say that the task is actually registered
        self.tasks[name].retry(args, kwargs, **options)

    def register(self, name, func):
        # XXX(dcramer): hacky way to ensure the task gets registered so
        # celery knows how to execute it
        self.tasks[name] = self.celery.task(func, name=name)


Celery = lambda **o: Container(_Celery, o, name='celery')
