import statsd
import re
import logging

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
        """Returns a Stats object.
        If no statsd config has been provided,
        the Stats won't do anything but validate."""
        if self._stats:
            return self._stats
        return Stats(client=None)


class Stats(object):
    """ Minimalistic class for sending stats/monitoring values."""

    def __init__(self, client):
        """
        @param client - A statsd.StatsClient instance, or None for a no-op Stats.
        """
        # A thin wrapper around Statsd rather than just Statsd so we
        # can pick which features to support and how to encode the data.
        self._client = client

    @swallow_exceptions(logger)
    def set_gauge(self, key, value):
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
        """ Record a millisecond timing. """
        assert isinstance(duration_ms, (int, float, long))
        Stats._check_key(key)
        if self._client:
            self._client.timing(key, duration_ms)

    _KEY_RE = re.compile(r'^[A-Za-z0-9_-]+$')

    @classmethod
    def _check_key(cls, key):
        """ This is probably overly strict, but we have little use for
        interestingly named keys and this avoids unintentionally using them."""
        if not cls._KEY_RE.match(key):
            raise Exception("Invalid key: {}".format(repr(key)))
