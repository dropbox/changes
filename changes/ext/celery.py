from __future__ import absolute_import

import logging

from celery import Celery as CeleryApp
from uuid import uuid4

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
        self.logger = logging.getLogger(app.name + '.celery')

    def delay(self, name, args=None, kwargs=None, *fn_args, **fn_kwargs):
        # We don't assume the task is registered at this point, so manually
        # publish it
        self.logger.debug('Firing task %r args=%r kwargs=%r', name, args, kwargs)
        celery = self.celery
        if celery.conf.CELERY_ALWAYS_EAGER:
            task_id = uuid4()
            # we dont call out to delay() as it causes db rollbacks/etc
            celery.tasks[name].run(*args or (), **kwargs or {})
        else:
            with celery.producer_or_acquire() as P:
                task_id = P.publish_task(
                    task_name=name,
                    task_args=args,
                    task_kwargs=kwargs,
                    *fn_args, **fn_kwargs
                )
        return task_id

    def retry(self, name, *args, **kwargs):
        # unlike delay, we actually want to rely on Celery's retry logic
        # and because we can only execute this within a task, it's safe
        # to say that the task is actually registered
        kwargs.setdefault('throw', False)
        self.tasks[name].retry(*args, **kwargs)

    def get_task(self, name):
        return self.tasks[name]

    def register(self, name, func, **kwargs):
        # XXX(dcramer): hacky way to ensure the task gets registered so
        # celery knows how to execute it
        for key, value in self.app.config['CELERY_ROUTES'].get(name, {}).iteritems():
            kwargs.setdefault(key, value)

        self.tasks[name] = self.celery.task(func, name=name, **kwargs)


def Celery(**o):
    return Container(_Celery, o, name='celery')
