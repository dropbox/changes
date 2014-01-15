from __future__ import absolute_import

import logging

from datetime import datetime, timedelta
from threading import local, Lock

from changes.config import db, queue
from changes.constants import Result, Status
from changes.models import Task
from changes.utils.locking import lock


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

    RETRY_COUNTDOWN = 60
    CONTINUE_COUNTDOWN = 5

    RUN_TIMEOUT = timedelta(minutes=5)
    EXPIRE_TIMEOUT = timedelta(minutes=60)

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

    def __call__(self, **kwargs):
        with self.lock:
            self._run(kwargs)

    def _run(self, kwargs):
        # commit any changes before we begin running hthe task
        db.session.commit()

        self.task_id = kwargs.pop('task_id', None)
        if not self.task_id:
            self.logger.warning('Missing task_id for job: %r', kwargs)
            with db.session.begin_nested():
                self.func(**kwargs)
            return

        self.parent_id = kwargs.pop('parent_task_id', None)
        self.kwargs = kwargs

        date_started = datetime.utcnow()

        try:
            self.func(**kwargs)

        except NotFinished:
            kwargs['task_id'] = self.task_id
            kwargs['parent_task_id'] = self.parent_id

            self._update({
                Task.date_modified: datetime.utcnow(),
                Task.status: Status.in_progress,
            })

            queue.delay(
                self.task_name,
                kwargs=kwargs,
                countdown=self.CONTINUE_COUNTDOWN,
            )

        except Exception as exc:
            db.session.rollback()

            self.logger.exception(unicode(exc))

            self._retry()

        else:
            date_finished = datetime.utcnow()

            self._update({
                Task.date_started: date_started,
                Task.date_finished: date_finished,
                Task.date_modified: date_finished,
                Task.status: Status.finished,
            })

        finally:
            db.session.commit()
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
        ).update(kwargs)

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

        kwargs = self.kwargs.copy()
        kwargs['task_id'] = self.task_id
        kwargs['parent_task_id'] = self.parent_id
        queue.retry(
            self.task_name,
            kwargs=kwargs,
            countdown=self.RETRY_COUNTDOWN,
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

        task = Task(
            task_name=self.task_name,
            parent_id=kwargs.get('parent_task_id'),
            task_id=kwargs['task_id'],
            status=Status.queued,
        )
        db.session.add(task)

        queue.delay(self.task_name, kwargs=kwargs)

    def verify_children(self, task_name, child_ids=(), kwarg_func=lambda x: {}):
        """
        Ensure all child tasks are running. If child_ids is
        present this will automatically manage creation of the any missing jobs.

        Return the aggregate status of child tasks.

        >>> child_status = task.ensure_all([1, 2], params=lambda child_id: {
        >>>     'job_id': child_id
        >>> })
        """
        assert self.task_id

        current_datetime = datetime.utcnow()
        run_datetime = current_datetime - self.RUN_TIMEOUT
        expire_datetime = current_datetime - self.EXPIRE_TIMEOUT

        task_list = list(Task.query.filter(
            Task.task_name == task_name,
            Task.parent_id == self.task_id,
        ))

        need_created = set(child_ids)
        need_expire = set()
        need_run = set()
        has_pending = False

        for task in task_list:
            try:
                need_created.remove(task.task_id.hex)
            except KeyError:
                pass

            if task.status == Status.finished:
                continue

            has_pending = True

            if task.date_modified < expire_datetime:
                need_expire.add(task.task_id)
            elif task.date_modified < run_datetime:
                need_run.add(task.task_id)

        if need_expire:
            Task.query.filter(
                Task.task_name == task_name,
                Task.parent_id == self.task_id,
                Task.task_id.in_([n for n in need_expire]),
            ).update({
                Task.date_modified: current_datetime,
                Task.status: Status.finished,
                Task.result: Result.aborted,
            })

        if need_run:
            Task.query.filter(
                Task.task_name == task_name,
                Task.parent_id == self.task_id,
                Task.task_id.in_([n for n in need_run]),
            ).update({
                Task.date_modified: current_datetime,
            })

        for child_id in need_created:
            child_task = Task(
                task_name=task_name,
                parent_id=self.task_id,
                task_id=child_id,
            )
            db.session.add(child_task)
            need_run.add(child_id)

        db.session.commit()

        for child_id in need_run:
            child_kwargs = kwarg_func(child_id)
            child_kwargs['parent_task_id'] = self.task_id
            child_kwargs['task_id'] = child_id
            queue.delay(task_name, kwargs=child_kwargs)

        if need_run or has_pending:
            status = Status.in_progress

        else:
            status = Status.finished

        return status


# bind to a decorator-like naming scheme
tracked_task = TrackedTask
