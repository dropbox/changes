import gevent

from collections import deque
from flask import Response, request, stream_with_context

from changes.config import pubsub
from changes.api.base import APIView, as_json


class EventStream(object):
    def __init__(self, pubsub):
        self.pubsub = pubsub
        self.pending = deque()
        self.active = True

        # TODO(dcramer): need to find a way to terminate these when the socket
        # is closed, but for now we time them out every 60s
        self.lifecycle = 60

        self.pubsub.subscribe('builds', self.push)

    def __iter__(self):
        while self.active:
            while self.pending:
                message = self.pending.pop()
                yield "data: {}\n\n".format(message)
                gevent.sleep(0)
            gevent.sleep(0.5)
        self.close()

    def push(self, message):
        self.pending.append(message)

    def close(self):
        self.pubsub.unsubscribe('builds', self.push)


class StreamAPIView(APIView):
    def get(self):
        stream = EventStream(pubsub)
        request.eventstream = stream
        return Response(stream_with_context(stream), mimetype='text/event-stream')


class TestStreamAPIView(APIView):
    def get(self):
        from datetime import datetime
        from changes.constants import Result, Status
        from changes.models import Build, Project, Author, Revision

        project = Project.query.all()[0]
        author = Author.query.all()[0]
        revision = Revision.query.all()[0]

        pubsub.publish('builds', as_json(Build(
            label='Test Build',
            project=project,
            author=author,
            status=Status.in_progress,
            result=Result.unknown,
            parent_revision_sha=revision.sha,
            date_created=datetime.utcnow(),
            date_started=datetime.utcnow(),
        )))

        return "ok!'"
