from __future__ import absolute_import

import logging

from datetime import datetime, timedelta
from functools import wraps
from threading import local, Lock, Timer
from uuid import uuid4
from contextlib import contextmanager

from changes.config import db, queue, statsreporter
from changes.constants import Result, Status
from changes.db.utils import get_or_create
from changes.models.task import Task
from changes.utils.locking import lock


BASE_RETRY_COUNTDOWN = 60
CONTINUE_COUNTDOWN = 5

# Number of seconds to delay before starting tasks.
# It isn't actually known whether this is useful or why we even have this delay;
# this just gives it a name so this fact is explicit and hopefully we can remove it more
# easily.
_DEFAULT_COUNTDOWN = 1

RUN_TIMEOUT = timedelta(minutes=60)
EXPIRE_TIMEOUT = timedelta(minutes=120)
HARD_TIMEOUT = timedelta(hours=12)

MAX_RETRIES = 10

# How many seconds we let tasks run before warning that they're slow.
_SLOW_RUN_THRESHOLD = 5 * 60


class NotFinished(Exception):
    def __init__(self, message=None, retry_after=None):
        super(NotFinished, self).__init__(message)
        self.retry_after = retry_after or CONTINUE_COUNTDOWN


class TooManyRetries(Exception):
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

    def __init__(self, func, max_retries=MAX_RETRIES, on_abort=None):
        self.func = lock(func)
        self.task_name = func.__name__
        self.parent_id = None
        self.task_id = None
        self.lock = Lock()
        self.logger = logging.getLogger('jobs.{0}'.format(self.task_name))

        self.max_retries = max_retries
        self.on_abort = on_abort

        # Whether to continue running the task even if we don't find it in the DB.
        # Intended for testing. Allowing this to be disabled makes it possible for
        # tests that have no interaction with the Task infrastructure to ignore the
        # TrackedTask wrapping.
        self.allow_absent_from_db = False

        self.__name__ = func.__name__
        self.__doc__ = func.__doc__
        self.__wraps__ = getattr(func, '__wraps__', func)
        self.__code__ = getattr(func, '__code__', None)

    def __call__(self, **kwargs):
        with statsreporter.stats().timer('task_duration_' + self.task_name):
            with self.lock:
                self._run(kwargs)

    def __repr__(self):
        return '<%s: task_name=%s>' % (type(self), self.task_name)

    def _run(self, kwargs):
        self.task_id = kwargs.pop('task_id', None)
        if self.task_id is None:
            self.task_id = uuid4().hex

        self.parent_id = kwargs.pop('parent_task_id', None)
        self.kwargs = kwargs

        date_started = datetime.utcnow()

        updated = self._update({
            Task.date_modified: datetime.utcnow(),
        })
        if not updated and not self.allow_absent_from_db:
            self.logger.error("Tried to update a Task that doesn't exist in the database; %s, %s",
                self.task_name, kwargs)
            return

        try:
            with self._report_slow(_SLOW_RUN_THRESHOLD, self.task_name):
                self.func(**kwargs)

        except NotFinished as e:
            self.logger.info(
                'Task marked as not finished: %s %s', self.task_name, self.task_id)

            self._continue(kwargs, e.retry_after)

        except Exception as exc:
            db.session.rollback()

            self.logger.exception(unicode(exc))

            try:
                self._retry()
            except TooManyRetries as exc:
                date_finished = datetime.utcnow()

                self._update({
                    Task.date_finished: date_finished,
                    Task.date_modified: date_finished,
                    Task.status: Status.finished,
                    Task.result: Result.failed,
                })
                self.logger.exception(unicode(exc))

                if self.on_abort:
                    self.on_abort(self)
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
                    Task.result: Result.passed,
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

        Returns:
           bool: Whether anything was updated.
        """
        assert self.task_id

        count = Task.query.filter(
            Task.task_name == self.task_name,
            Task.task_id == self.task_id,
            Task.parent_id == self.parent_id,
        ).update(kwargs, synchronize_session=False)
        return bool(count)

    def _continue(self, kwargs, retry_after=CONTINUE_COUNTDOWN):
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
            countdown=retry_after,
        )

    def _retry(self):
        """
        Retry this task and update it's state.

        >>> task.retry()
        """
        # TODO(dcramer): this needs to handle too-many-retries itself
        assert self.task_id

        task = Task.query.filter(
            Task.task_name == self.task_name,
            Task.task_id == self.task_id,
            Task.parent_id == self.parent_id,
        ).first()
        if task and self.max_retries and task.num_retries > self.max_retries:
            date_finished = datetime.utcnow()
            self._update({
                Task.date_finished: date_finished,
                Task.date_modified: date_finished,
                Task.status: Status.finished,
                Task.result: Result.failed,
            })
            db.session.commit()

            raise TooManyRetries('%s failed after %d retries' % (self.task_name, task.num_retries))

        self._update({
            Task.date_modified: datetime.utcnow(),
            Task.status: Status.in_progress,
            Task.num_retries: Task.num_retries + 1,
        })

        db.session.commit()

        kwargs = self.kwargs.copy()
        kwargs['task_id'] = self.task_id
        kwargs['parent_task_id'] = self.parent_id

        retry_number = db.session.query(Task.num_retries).filter(
            Task.task_name == self.task_name,
            Task.task_id == self.task_id,
            Task.parent_id == self.parent_id,
        ).scalar() or 0

        retry_countdown = min(BASE_RETRY_COUNTDOWN + (retry_number ** 2), 300)

        queue.delay(
            self.task_name,
            kwargs=kwargs,
            countdown=retry_countdown,
        )

    def needs_requeued(self, task):
        if self.max_retries and task.num_retries >= self.max_retries:
            return False

        current_datetime = datetime.utcnow()

        timeout_datetime = current_datetime - HARD_TIMEOUT
        if task.date_created < timeout_datetime:
            return False

        run_datetime = current_datetime - RUN_TIMEOUT
        return task.date_modified < run_datetime

    def needs_expired(self, task):
        if self.max_retries and task.num_retries >= self.max_retries:
            return True

        current_datetime = datetime.utcnow()

        timeout_datetime = current_datetime - HARD_TIMEOUT
        if task.date_created < timeout_datetime:
            return True

        expire_datetime = current_datetime - EXPIRE_TIMEOUT
        if task.date_modified < expire_datetime:
            return True

        return False

    def delay_if_needed(self, **kwargs):
        """
        Enqueue this task if it's new or hasn't checked in in a reasonable
        amount of time.

        >>> task.delay_if_needed(
        >>>     task_id='33846695b2774b29a71795a009e8168a',
        >>>     parent_task_id='659974858dcf4aa08e73a940e1066328',
        >>> )
        """
        kwargs.setdefault('task_id', uuid4().hex)

        fn_kwargs = dict(
            (k, v) for k, v in kwargs.iteritems()
            if k not in ('task_id', 'parent_task_id')
        )

        task, created = get_or_create(Task, where={
            'task_name': self.task_name,
            'task_id': kwargs['task_id'],
        }, defaults={
            'parent_id': kwargs.get('parent_task_id'),
            'data': {
                'kwargs': fn_kwargs,
            },
            'status': Status.queued,
        })

        if created or self.needs_requeued(task):
            if not created:
                task.date_modified = datetime.utcnow()
                db.session.add(task)

            db.session.commit()

            queue.delay(
                self.task_name,
                kwargs=kwargs,
                countdown=_DEFAULT_COUNTDOWN,
            )

        if created:
            self._report_created()

    def delay(self, **kwargs):
        """
        Enqueue this task.

        >>> task.delay(
        >>>     task_id='33846695b2774b29a71795a009e8168a',
        >>>     parent_task_id='659974858dcf4aa08e73a940e1066328',
        >>> )
        """
        kwargs.setdefault('task_id', uuid4().hex)

        fn_kwargs = dict(
            (k, v) for k, v in kwargs.iteritems()
            if k not in ('task_id', 'parent_task_id')
        )

        task, created = get_or_create(Task, where={
            'task_name': self.task_name,
            'task_id': kwargs['task_id'],
        }, defaults={
            'parent_id': kwargs.get('parent_task_id'),
            'data': {
                'kwargs': fn_kwargs,
            },
            'status': Status.queued,
        })

        if not created:
            task.date_modified = datetime.utcnow()
            db.session.add(task)

        db.session.commit()

        if created:
            self._report_created()

        queue.delay(
            self.task_name,
            kwargs=kwargs,
            countdown=_DEFAULT_COUNTDOWN,
        )

    def verify_all_children(self):
        task_list = list(Task.query.filter(
            Task.parent_id == self.task_id,
            Task.status != Status.finished,
        ))

        if not task_list:
            return Status.finished

        current_datetime = datetime.utcnow()

        need_expire = set()
        need_run = set()

        has_pending = False

        for task in task_list:
            if self.needs_expired(task):
                need_expire.add(task)
                continue

            has_pending = True

            if self.needs_requeued(task) and 'kwargs' in task.data:
                need_run.add(task)

        if need_expire:
            Task.query.filter(
                Task.id.in_([n.id for n in need_expire]),
            ).update({
                Task.date_modified: current_datetime,
                Task.date_finished: current_datetime,
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

    def _report_created(self):
        """Reports to monitoring that a new Task was created."""
        statsreporter.stats().incr('new_task_created_' + self.task_name)

    @contextmanager
    def _report_slow(self, threshold, msg):
        """Reports a warning if the wrapped code is taking too long
        Args:
            threshold (int): Time to wait before warning, in seconds.
            msg (str): Message to be included in the report.
        """
        def report():
            self.logger.warning("Task taking too long ({}s so far): {}", threshold, msg)
        t = Timer(threshold, report)
        t.start()
        try:
            yield
        finally:
            t.cancel()


# bind to a decorator-like naming scheme
def tracked_task(func=None, **kwargs):
    def wrapped(func):
        return wraps(func)(TrackedTask(func, **kwargs))

    if func:
        return wraps(func)(wrapped(func))
    return wrapped
