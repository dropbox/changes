from __future__ import absolute_import

import json
import gevent
import redis

from collections import defaultdict
from flask import _app_ctx_stack
from fnmatch import fnmatch
from uuid import uuid4


default_config = {
    'REDIS_URL': 'redis://localhost:6379',
}


def get_state(app):
    """Gets the state for the application"""
    assert 'pubsub' in app.extensions, \
        'The pubsub extension was not registered to the current ' \
        'application.  Please make sure to call init_app() first.'
    return app.extensions['pubsub']


class _PubSubState(object):
    # TODO(dcramer): currently we listen to all messages based on the idea
    # that at least one connected client needs to know
    def __init__(self, ext, app):
        self.ext = ext
        self.app = app

        self._callbacks = defaultdict(set)
        self._channel = 't_' + uuid4().hex

        self._redis = self.get_connection()
        self._pubsub = self._redis.pubsub()

        self._spawn(self._redis_listen)

    def _spawn(self, *args, **kwargs):
        return gevent.spawn(*args, **kwargs).link_exception(self._log_error)

    def _log_error(self, greenlet):
        self.app.logger.error(unicode(greenlet.exception))

    def get_connection(self):
        return redis.from_url(self.app.config['REDIS_URL'])

    def publish(self, channel, data):
        self._spawn(self._redis.publish, channel, json.dumps(data))

    def subscribe(self, channel, callback):
        self._callbacks[channel].add(callback)
        self.app.logger.info(
            'Channel {%s} has %d subscriber(s)', channel,
            len(self._callbacks[channel]))

    def unsubscribe(self, channel, callback):
        try:
            self._callbacks[channel].remove(callback)
        except KeyError:
            return

        self.app.logger.info(
            'Channel {%s} has %d subscriber(s)',
            channel, len(self._callbacks[channel]))

    def _process_msg(self, msg):
        if msg.get('type') in ('psubscribe', 'psubscribe'):
            return

        channel = msg['channel']
        data = json.loads(msg['data'])
        # XXX(dcramer): this code can be run concurrently so its important
        # to note that callbacks can change size/contents during iteration
        for pattern, callbacks in self._callbacks.items():
            if not fnmatch(channel, pattern):
                continue
            # because callbacks is shared, we copy the set into a new list
            # to ensure it doesnt change during iteration
            for cb in list(callbacks):
                self._spawn(cb, data)
            gevent.sleep(0)

    def _redis_listen(self):
        self._pubsub.psubscribe('*')
        for msg in self._pubsub.listen():
            try:
                self._spawn(self._process_msg, msg)
            except Exception as exc:
                self.app.logger.warn(
                    'Could not process message: %s', exc, exc_info=True)
            gevent.sleep(0)


class PubSub(object):
    def __init__(self, app=None):
        self.app = None

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.app = app

        for key, value in default_config.items():
            app.config.setdefault(key, value)

        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['pubsub'] = _PubSubState(self, app)

    def get_app(self, reference_app=None):
        if reference_app is not None:
            return reference_app
        if self.app is not None:
            return self.app
        ctx = _app_ctx_stack.top
        if ctx is not None:
            return ctx.app
        raise RuntimeError('application not registered on db '
                           'instance and no application bound '
                           'to current context')

    def publish(self, *args, **kwargs):
        return self.get_app().extensions['pubsub'].publish(*args, **kwargs)

    def subscribe(self, *args, **config):
        return self.get_app().extensions['pubsub'].subscribe(*args, **config)

    def unsubscribe(self, *args, **config):
        return self.get_app().extensions['pubsub'].unsubscribe(*args, **config)
