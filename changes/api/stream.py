from changes.config import pubsub
from changes.api.base import APIView, as_json


class TestStreamAPIView(APIView):
    def get(self):
        from datetime import datetime
        from changes.constants import Result, Status
        from changes.models import Build, Project, Author, Revision

        project = Project.query.all()[0]
        author = Author.query.all()[0]
        revision = Revision.query.all()[0]

        pubsub.publish('builds', {
            'data': as_json(Build(
                label='Test Build',
                project=project,
                author=author,
                status=Status.in_progress,
                result=Result.unknown,
                parent_revision_sha=revision.sha,
                date_created=datetime.utcnow(),
                date_started=datetime.utcnow(),
            )),
            'event': 'build',
        })

        return "ok!'"
