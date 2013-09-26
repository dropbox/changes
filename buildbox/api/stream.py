import time

from collections import deque
from flask import Response

from buildbox.config import pubsub
from buildbox.api.base import APIView, as_json


class EventStream(object):
    def __init__(self, redis, channel):
        self.pending = deque()
        pubsub.subscribe('builds', self.push)

    def __iter__(self):
        while True:
            while self.pending:
                message = self.pending.pop()
                yield "data: %s\n\n" % (message,)
            time.sleep(0.2)

    def push(self, message):
        self.pending.append(message)


class StreamAPIView(APIView):
    def get(self):
        stream = EventStream(pubsub, 'builds')

        # self.set_header("Cache-Control", "no-cache")
        return Response(stream, mimetype='text/event-stream')


class TestStreamAPIView(APIView):
    def get(self):
        from datetime import datetime
        from buildbox.constants import Result, Status
        from buildbox.models import Build, Project, Author, Revision

        project = Project.query.all()[0]
        author = Author.query.all()[0]
        revision = Revision.query.all()[0]

        pubsub.publish('builds', as_json(Build(
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
