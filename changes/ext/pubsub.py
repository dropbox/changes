import gevent
import redis

from uuid import uuid4

from flask import _app_ctx_stack

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
    def __init__(self, ext, app):
        self.ext = ext
        self.app = app

        self._callbacks = {}
        self._channel = 't_' + uuid4().hex

        self._redis = self.get_connection()
        self._pubsub = self._redis.pubsub()
        self._pubsub.subscribe(self._channel)

        gevent.spawn(self._redis_listen)
        # listener = Thread(target=self._redis_listen)
        # listener.setDaemon(True)
        # listener.start()

    def get_connection(self):
        return redis.from_url(self.app.config['REDIS_URL'])

    def publish(self, channel, data):
        self._redis.publish(channel, data)

    def subscribe(self, channel, callback):
        local_subs = self._callbacks.get(channel, None)
        if local_subs is None:
            local_subs = {callback}
            self._callbacks[channel] = local_subs
            self._redis.publish(self._channel, 'subscribe:' + channel)
        else:
            local_subs.add(callback)
        self.app.logger.info('Channel {%s} has %d subscriber(s)', channel, len(local_subs))

    def unsubscribe(self, channel, callback):
        local_subs = self._callbacks.get(channel, None)
        if local_subs is None:
            return
        local_subs.remove(callback)
        self.app.logger.info('Channel {%s} has %d subscriber(s)', channel, len(local_subs))
        if local_subs:
            return
        self._redis.publish(self._channel, 'unsubscribe:' + channel)
        del self._callbacks[channel]

    def _process_msg(self, msg):
        channel = msg['channel']
        data = msg['data']
        if msg.get('type', None) == 'subscribe' or msg.get('type') == 'unsubscribe':
            return
        elif channel == self._channel:
            command = data.split(':')
            if command[0] == 'subscribe':
                self._pubsub.subscribe(command[1])
            elif command[0] == 'unsubscribe':
                self._pubsub.unsubscribe(command[1])
            else:
                self.app.logger.warn('Unknown command: %s', command[0])
        else:
            for cb in self._callbacks.get(channel, []):
                cb(data)
                gevent.sleep(0)

    def _redis_listen(self):
        for msg in self._pubsub.listen():
            try:
                self._process_msg(msg)
            except Exception as exc:
                self.app.logger.warn('Could not process message: %s', exc, exc_info=True)


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
