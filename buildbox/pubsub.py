import gevent.thread
import logging
import uuid

from flask import _app_ctx_stack
from redis import StrictRedis
from weakref import WeakSet

logger = logging.getLogger('pubsub')


def get_state(app):
    """Gets the state for the application"""
    assert 'pubsub' in app.extensions, \
        'The pubsub extension was not registered to the current ' \
        'application.  Please make sure to call init_app() first.'
    return app.extensions['pubsub']


class _PubSubState(object):
    def __init__(self, ext, app):
        self.ext = ext
        self.app = app

        self._callbacks = {}
        self._cmd_channel = 't_' + uuid.uuid4().hex

        self._redis = StrictRedis(**app.config['PUBSUB_CONNECTION'])
        self._pubsub = self._redis.pubsub()
        self._pubsub.subscribe(self._cmd_channel)

        gevent.thread.start_new_thread(self._redis_listen)

    def publish(self, channel, data):
        self.app.logger.info('Publishing message to {%s}: %s', channel, data)
        self._redis.publish(channel, data)

    def subscribe(self, channel, callback):
        local_subs = self._callbacks.get(channel, None)
        if local_subs is None:
            self.app.logger.info('Subscribing to channel {%s}', channel)
            local_subs = WeakSet([callback])
            self._callbacks[channel] = local_subs
            self._redis.publish(self._cmd_channel, 'subscribe:' + channel)
        else:
            local_subs.add(callback)

        self.app.logger.info('%d subscribers to {%s}', len(local_subs), channel)

    def unsubscribe(self, channel, callback):
        local_subs = self._callbacks.get(channel, None)
        if local_subs is None:
            return

        local_subs.remove(callback)

        self.app.logger.info('%d subscribers to {%s}', len(local_subs), channel)

        if local_subs:
            return
        self._redis.publish(self._cmd_channel, 'unsubscribe:' + channel)
        del self._callbacks[channel]

    def _process_msg(self, msg):
        channel = msg['channel']
        data = msg['data']
        if msg.get('type', None) == 'subscribe' or msg.get('type') == 'unsubscribe':
            return
        elif channel == self._cmd_channel:
            command = data.split(':')
            if command[0] == 'subscribe':
                self._pubsub.subscribe(command[1])
            elif command[0] == 'unsubscribe':
                self._pubsub.unsubscribe(command[1])
            else:
                logger.warn('Unknown command: %s', command[0])
        else:
            # dispatch callbacks
            for callback in self._callbacks.get(channel, []):
                print callback, data
                callback(data)

    def _redis_listen(self):
        for msg in self._pubsub.listen():
            self.app.logger.info('Got message: %s', msg)
            try:
                self._process_msg(msg)
            except Exception as exc:
                self.app.logger.warn('Could not process message: %s', exc, exc_info=True)


class PubSub(object):
    def __init__(self, app=None):
        if app is not None:
            self.app = app
            self.init_app(app)
        else:
            self.app = None

    def init_app(self, app):
        self.app = app
        app.config.setdefault('PUBSUB_CONNECTION', {})

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

    # TODO(dcramer): is there a better pattern for this?
    def publish(self, channel, data):
        state = get_state(self.get_app())
        state.publish(channel, data)

    def subscribe(self, channel, callback):
        state = get_state(self.get_app())
        state.subscribe(channel, callback)

    def unsubscribe(self, channel, callback):
        state = get_state(self.get_app())
        state.unsubscribe(channel, callback)
