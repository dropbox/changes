import gevent

from threading import Thread

from collections import deque
from flask import Response

from buildbox.config import redis
from buildbox.api.base import APIView, as_json


class EventStream(object):
    def __init__(self, redis):
        self.redis = redis
        self.pending = deque()

        self.listener = Thread(target=self.stream)
        self.listener.setDaemon(True)
        self.listener.start()

    def __iter__(self):
        while True:
            while self.pending:
                message = self.pending.pop()
                if not isinstance(message['data'], basestring):
                    continue
                yield "data: {}\n\n".format(message['data'])
                gevent.sleep(0.01)
            gevent.sleep(0.3)

    def push(self, message):
        self.pending.append(message)

    def stream(self):
        pubsub = self.redis.pubsub()
        pubsub.subscribe('builds')
        for message in pubsub.listen():
            self.push(message)
            gevent.sleep(0.01)


class StreamAPIView(APIView):
    def get(self):
        # self.stream = EventStream()
        return Response(EventStream(redis), mimetype='text/event-stream')


class TestStreamAPIView(APIView):
    def get(self):
        from datetime import datetime
        from buildbox.constants import Result, Status
        from buildbox.models import Build, Project, Author, Revision

        project = Project.query.all()[0]
        author = Author.query.all()[0]
        revision = Revision.query.all()[0]

        redis.publish('builds', as_json(Build(
            label='Test Build',
            project=project,
            author=author,
            status=Status.in_progress,
            result=Result.unknown,
            parent_revision=revision,
            date_created=datetime.utcnow(),
            date_started=datetime.utcnow(),
        )))

        return "ok!'"
