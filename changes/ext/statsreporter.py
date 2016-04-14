import re
import time
import logging
from contextlib import contextmanager
from functools import wraps
from typing import Iterator, Optional

import statsd

logger = logging.getLogger('statsreporter')


def swallow_exceptions(exn_logger):
    """Decorator to catch, log, and discard any Exceptions raised in a method.
    :param exn_logger: logging.Logger to use for logging any exceptions.
    """
    def decor(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                exn_logger.exception(e)
        return wrapper
    return decor


class StatsReporter(object):
    """StatsReporter is responsible for maintaining an app-specific Stats instance.
    The app config should specify:
       STATSD_HOST (address of statsd host as a string)
       STATSD_PORT (port statsd is listening on as an int)
       STATSD_PREFIX (string to be automatically prepended to all reported stats for namespacing)

    If STATSD_HOST isn't specified, none of the others will be used and this app will
    get a no-op Stats instance.
    """
    def __init__(self, app=None):
        self.app = app
        self._stats = None
        if app:
            self.init_app(app)

    def init_app(self, app):
        if not self._stats and app.config.get('STATSD_HOST'):
            sd = statsd.StatsClient(host=app.config['STATSD_HOST'],
                                    prefix=app.config['STATSD_PREFIX'],
                                    port=app.config['STATSD_PORT'])
            self._stats = Stats(client=sd)

    def stats(self):
        # type: () -> Stats
        """Returns a Stats object.
        If no statsd config has been provided,
        the Stats won't do anything but validate."""
        if self._stats:
            return self._stats
        return Stats(client=None)

    def timer(self, key):
        """Decorator to report timing for a function.
        The decorator method is on this class instead of Stats to ensure that the
        current Stats instance at method invocation time is used instead of the
        Stats instance available at decoration time (which may be the no-op instance).
        Args:
            key (str): Name to report the timing with.
        """
        Stats._check_key(key)  # fail early if it's a bad key.

        def wrapper(fn):
            @wraps(fn)
            def inner(*args, **kwargs):
                with self.stats().timer(key):
                    return fn(*args, **kwargs)
            return inner
        return wrapper


class Stats(object):
    """ Minimalistic class for sending stats/monitoring values."""

    def __init__(self, client):
        # type: (Optional[statsd.StatsClient]) -> None
        """
        @param client - A statsd.StatsClient instance, or None for a no-op Stats.
        """
        # A thin wrapper around Statsd rather than just Statsd so we
        # can pick which features to support and how to encode the data.
        self._client = client

    @swallow_exceptions(logger)
    def set_gauge(self, key, value):
        # type: (bytes, float) -> None
        """ Set a gauge, typically a sampled instantaneous value.
            @param key - the name of the gauge.
            @param value - current value of the gauge.
        """
        assert isinstance(value, (int, float, long))
        Stats._check_key(key)
        if self._client:
            self._client.gauge(key, value)

    @swallow_exceptions(logger)
    def incr(self, key, delta=1):
        # type: (bytes, float) -> None
        """ Increment a count.
            @param key - the name of the stat.
            @param delta - amount to increment the stat by. Must be positive.
        """
        assert isinstance(delta, (int, float, long))
        assert delta >= 0
        Stats._check_key(key)
        if self._client:
            self._client.incr(key, delta)

    @swallow_exceptions(logger)
    def log_timing(self, key, duration_ms):
        # type: (bytes, float) -> None
        """ Record a millisecond timing. """
        assert isinstance(duration_ms, (int, float, long))
        Stats._check_key(key)
        if self._client:
            self._client.timing(key, duration_ms)

    @contextmanager
    def timer(self, key):
        # type: (bytes) -> Iterator[None]
        """A contextmanager that reports the duration in milliseconds on exit."""
        t0 = time.time()
        try:
            yield
        finally:
            duration_ms = int(1000 * (time.time() - t0))
            self.log_timing(key, duration_ms)

    _KEY_RE = re.compile(r'^[A-Za-z0-9_-]+$')

    @classmethod
    def _check_key(cls, key):
        # type: (bytes) -> None
        """ This is probably overly strict, but we have little use for
        interestingly named keys and this avoids unintentionally using them."""
        if not cls._KEY_RE.match(key):
            raise Exception("Invalid key: {}".format(repr(key)))
