from __future__ import absolute_import

import gevent

from collections import deque

from changes.config import pubsub


class EventStream(object):
    def __init__(self, channels, pubsub=pubsub):
        self.pubsub = pubsub
        self.pending = deque()
        self.channels = channels
        self.active = True

        for channel in channels:
            self.pubsub.subscribe(channel, self.push)

    def __iter__(self):
        while self.active:
            # TODO(dcramer): figure out why we have to send this to ensure
            # the connection is opened
            yield "\n"
            while self.pending:
                event = self.pending.pop()
                yield "event: {}\n".format(event['event'])
                for line in event['data'].splitlines():
                    yield "data: {}\n".format(line)
                yield "\n"
                gevent.sleep(0)
            gevent.sleep(1)

    def __del__(self):
        self.close()

    def push(self, message):
        self.pending.append(message)

    def close(self):
        for channel in self.channels:
            self.pubsub.unsubscribe(channel, self.push)
