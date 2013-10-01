from datetime import datetime

from changes.api.base import APIView, as_json
from changes.config import pubsub
from changes.constants import Result, Status
from changes.models import Change, Build, Project, Author, Revision


class TestStreamAPIView(APIView):
    def get(self):
        project = Project.query.all()[0]
        author = Author.query.all()[0]
        revision = Revision.query.all()[0]
        build = Build(
            change=Change(label='Test Change'),
            label='Test Build',
            project=project,
            author=author,
            status=Status.in_progress,
            result=Result.unknown,
            parent_revision_sha=revision.sha,
            date_created=datetime.utcnow(),
            date_started=datetime.utcnow(),
        )

        channel = 'builds:{0}:{1}'.format(build.change_id.hex, build.id.hex)
        pubsub.publish(channel, {
            'data': as_json(build),
            'event': 'build',
        })

        return "ok!'"
