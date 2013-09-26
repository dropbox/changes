import gevent

from flask import Response
from redis import StrictRedis

from buildbox.api.base import APIView, as_json


class StreamAPIView(APIView):
    def get(self):
        def event_stream():
            redis = StrictRedis()
            pubsub = redis.pubsub()
            pubsub.subscribe('builds')

            for message in pubsub.listen():
                if not isinstance(message['data'], basestring):
                    continue
                yield "data: {}\n\n".format(message['data'])
                gevent.sleep(0.01)

        # self.stream = EventStream()
        return Response(event_stream(), mimetype='text/event-stream')


class TestStreamAPIView(APIView):
    def get(self):
        redis = StrictRedis()

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
