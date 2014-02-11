from __future__ import absolute_import

import logging

from datetime import datetime, timedelta
from threading import local, Lock

from changes.config import db, queue
from changes.constants import Result, Status
from changes.db.utils import try_create, get_or_create
from changes.models import Task
from changes.utils.locking import lock


RETRY_COUNTDOWN = 60
CONTINUE_COUNTDOWN = 5

RUN_TIMEOUT = timedelta(minutes=5)
EXPIRE_TIMEOUT = timedelta(minutes=30)


def needs_requeued(task):
    current_datetime = datetime.utcnow()
    run_datetime = current_datetime - RUN_TIMEOUT
    return task.date_modified < run_datetime


def needs_expired(task):
    current_datetime = datetime.utcnow()
    expire_datetime = current_datetime - EXPIRE_TIMEOUT
    return task.date_modified < expire_datetime


class NotFinished(Exception):
    pass


class TrackedTask(local):
    """
    Tracks the state of the given Task and it's children.

    Tracked tasks **never** return a result.

    >>> @tracked_task
    >>> def func(foo):
    >>>    if random.randint(0, 1) == 1:
    >>>        # re-queue for further results
    >>>        raise func.NotFinished
    >>>
    >>>    elif random.randint(0, 1) == 1:
    >>>        # cause an exception to retry
    >>>        raise Exception
    >>>
    >>>    # finish normally to update Status
    >>>    print "func", foo

    >>> foo.delay(foo='bar', task_id='bar')
    """
    NotFinished = NotFinished

    def __init__(self, func):
        self.func = lock(func)
        self.task_name = func.__name__
        self.parent_id = None
        self.task_id = None
        self.lock = Lock()
        self.logger = logging.getLogger('jobs.{0}'.format(self.task_name))

        self.__name__ = func.__name__
        self.__doc__ = func.__doc__
        self.__wraps__ = getattr(func, '__wraps__', func)
        self.__code__ = getattr(func, '__code__', None)

    def __call__(self, **kwargs):
        with self.lock:
            self._run(kwargs)

    def _run(self, kwargs):
        self.task_id = kwargs.pop('task_id', None)
        if not self.task_id:
            self.logger.warning('Missing task_id for job: %r', kwargs)
            self.func(**kwargs)
            return

        self.parent_id = kwargs.pop('parent_task_id', None)
        self.kwargs = kwargs

        date_started = datetime.utcnow()

        try:
            self.func(**kwargs)

        except NotFinished:
            self.logger.info(
                'Task marked as not finished: %s %s', self.task_name, self.task_id)

            self._continue(kwargs)

        except Exception as exc:
            db.session.rollback()

            self.logger.exception(unicode(exc))

            try:
                self._retry()
            except Exception as exc:
                self.logger.exception(unicode(exc))
                raise

        else:
            date_finished = datetime.utcnow()

            try:
                self._update({
                    Task.date_started: date_started,
                    Task.date_finished: date_finished,
                    Task.date_modified: date_finished,
                    Task.status: Status.finished,
                })
            except Exception as exc:
                self.logger.exception(unicode(exc))
                raise

            db.session.commit()
        finally:
            db.session.expire_all()

            self.task_id = None
            self.parent_id = None
            self.kwargs = kwargs

    def _update(self, kwargs):
        """
        Update's the state of this Task.

        >>> task._update(status=Status.finished)
        """
        assert self.task_id

        Task.query.filter(
            Task.task_name == self.task_name,
            Task.parent_id == self.parent_id,
            Task.task_id == self.task_id,
        ).update(kwargs, synchronize_session=False)

    def _continue(self, kwargs):
        kwargs['task_id'] = self.task_id
        kwargs['parent_task_id'] = self.parent_id

        self._update({
            Task.date_modified: datetime.utcnow(),
            Task.status: Status.in_progress,
        })

        db.session.commit()

        queue.delay(
            self.task_name,
            kwargs=kwargs,
            countdown=CONTINUE_COUNTDOWN,
        )

    def _retry(self):
        """
        Retry this task and update it's state.

        >>> task.retry()
        """
        # TODO(dcramer): this needs to handle too-many-retries itself
        assert self.task_id

        self._update({
            Task.date_modified: datetime.utcnow(),
            Task.status: Status.in_progress,
            Task.num_retries: Task.num_retries + 1,
        })

        db.session.commit()

        kwargs = self.kwargs.copy()
        kwargs['task_id'] = self.task_id
        kwargs['parent_task_id'] = self.parent_id

        queue.delay(
            self.task_name,
            kwargs=kwargs,
            countdown=RETRY_COUNTDOWN,
        )

    def delay_if_needed(self, **kwargs):
        """
        Enqueue this task if it's new or hasn't checked in in a reasonable
        amount of time.

        >>> task.delay_if_needed(
        >>>     task_id='33846695b2774b29a71795a009e8168a',
        >>>     parent_task_id='659974858dcf4aa08e73a940e1066328',
        >>> )
        """
        assert kwargs.get('task_id')

        fn_kwargs = dict(
            (k, v) for k, v in kwargs.iteritems()
            if k not in ('task_id', 'parent_task_id')
        )

        task, created = get_or_create(Task, where={
            'task_name': self.task_name,
            'parent_id': kwargs.get('parent_task_id'),
            'task_id': kwargs['task_id'],
        }, defaults={
            'data': {
                'kwargs': fn_kwargs,
            },
            'status': Status.queued,
        })

        if created or needs_requeued(task):
            db.session.commit()

            queue.delay(
                self.task_name,
                kwargs=kwargs,
                countdown=CONTINUE_COUNTDOWN,
            )

    def delay(self, **kwargs):
        """
        Enqueue this task.

        >>> task.delay(
        >>>     task_id='33846695b2774b29a71795a009e8168a',
        >>>     parent_task_id='659974858dcf4aa08e73a940e1066328',
        >>> )
        """
        assert kwargs.get('task_id')

        fn_kwargs = dict(
            (k, v) for k, v in kwargs.iteritems()
            if k not in ('task_id', 'parent_task_id')
        )

        try_create(Task, where={
            'task_name': self.task_name,
            'parent_id': kwargs.get('parent_task_id'),
            'task_id': kwargs['task_id'],
            'status': Status.queued,
            'data': {
                'kwargs': fn_kwargs,
            },
        })

        db.session.commit()

        queue.delay(
            self.task_name,
            kwargs=kwargs,
            countdown=CONTINUE_COUNTDOWN,
        )

    def verify_all_children(self):
        task_list = list(Task.query.filter(
            Task.parent_id == self.task_id
        ))

        current_datetime = datetime.utcnow()

        need_expire = set()
        need_run = set()

        has_pending = False

        for task in task_list:
            if task.status == Status.finished:
                continue

            if needs_expired(task):
                need_expire.add(task)
                continue

            has_pending = True

            if needs_requeued(task) and 'kwargs' in task.data:
                need_run.add(task)

        if need_expire:
            Task.query.filter(
                Task.id.in_([n.id for n in need_expire]),
            ).update({
                Task.date_modified: current_datetime,
                Task.status: Status.finished,
                Task.result: Result.aborted,
            }, synchronize_session=False)
            db.session.commit()

        if need_run:
            for task in need_run:
                child_kwargs = task.data['kwargs'].copy()
                child_kwargs['parent_task_id'] = task.parent_id.hex
                child_kwargs['task_id'] = task.task_id.hex
                queue.delay(task.task_name, kwargs=child_kwargs)

            Task.query.filter(
                Task.id.in_([n.id for n in need_run]),
            ).update({
                Task.date_modified: current_datetime,
            }, synchronize_session=False)
            db.session.commit()

        if has_pending:
            status = Status.in_progress

        else:
            status = Status.finished

        return status


# bind to a decorator-like naming scheme
tracked_task = TrackedTask
