import functools
import logging
import tornado.web
import threading
import uuid

from redis import StrictRedis
from tornado.ioloop import IOLoop

logger = logging.getLogger('pubsub')


class BuildboxServer(tornado.web.Application):
    def __init__(self, *args, **kwargs):
        """
        In addition to invoking the superclass constructor, initializes the per-server redis client and per-server
        redis pubsub handler.
        """
        redis_conf = kwargs.pop('redis', {})

        super(BuildboxServer, self).__init__(*args, **kwargs)

        self._pubsub_callbacks = {}
        self._pubsub_cmd_channel = 't_' + uuid.uuid4().hex

        self._redis = StrictRedis(**redis_conf)
        self._pubsub = self._redis.pubsub()
        self._pubsub.subscribe(self._pubsub_cmd_channel)

        listener = threading.Thread(target=self._redis_listen)
        listener.setDaemon(True)
        listener.start()

    def publish(self, channel, data):
        logger.info('Publishing message to {%s}: %s', channel, data)
        self._redis.publish(channel, data)

    def subscribe(self, channel, callback):
        """
        Only channel subscriptions are supported, not pattern subs.
        Callback should take one argument, which is the received message data.
        Creating the subscription is a blocking call to the redis client.  That is, this call will block until
        the subscription is registered; it will _not_ block waiting for messages on the subscribed channel.
        """
        logger.info('Subscribing to channel {%s} with {%s}', channel, callback)
        local_subs = self._pubsub_callbacks.get(channel, None)
        if local_subs is None:
            local_subs = {callback}
            self._pubsub_callbacks[channel] = local_subs
            self._redis.publish(self._pubsub_cmd_channel, 'subscribe:' + channel)
        else:
            local_subs.add(callback)

    def unsubscribe(self, channel, callback):
        local_subs = self._pubsub_callbacks.get(channel, None)
        if local_subs is None:
            return
        local_subs.remove(callback)
        if local_subs:
            return
        self._redis.publish(self._pubsub_cmd_channel, 'unsubscribe:' + channel)
        del self._pubsub_callbacks[channel]

    def _process_msg(self, msg):
        channel = msg['channel']
        data = msg['data']
        if msg.get('type', None) == 'subscribe' or msg.get('type') == 'unsubscribe':
            return
        elif channel == self._pubsub_cmd_channel:
            command = data.split(':')
            if command[0] == 'subscribe':
                self._pubsub.subscribe(command[1])
            elif command[0] == 'unsubscribe':
                self._pubsub.unsubscribe(command[1])
            else:
                logger.warn('Unknown command: %s', command[0])
        else:
            listeners = self._pubsub_callbacks.get(channel, [])
            for listener in listeners:
                IOLoop.instance().add_callback(functools.partial(listener, data))

    def _redis_listen(self):
        for msg in self._pubsub.listen():
            try:
                self._process_msg(msg)
            except Exception as exc:
                logger.warn('Could not process message: %s', exc, exc_info=True)
