from flask import Response
from sqlalchemy.orm import joinedload, subqueryload_all

from datetime import datetime

from changes.api.base import APIView
from changes.config import db, queue
from changes.constants import Cause, Status
from changes.models import Build


class BuildRetryAPIView(APIView):
    def post(self, build_id):
        build = Build.query.options(
            subqueryload_all(Build.phases),
            joinedload(Build.project),
            joinedload(Build.author),
        ).get(build_id)
        if build is None:
            return Response(status=404)

        new_build = Build(
            change=build.change,
            repository=build.repository,
            project=build.project,
            parent_revision_sha=build.parent_revision_sha,
            parent_id=build.id,
            patch=build.patch,
            label=build.label,
            status=Status.queued,
            message=build.message,
            # TODO(dcramer): author is a lie
            author=build.author,
            cause=Cause.retry,
        )

        # TODO: some of this logic is repeated from the create build endpoint
        if new_build.change:
            new_build.change.date_modified = datetime.utcnow()
            db.session.add(new_build.change)

        db.session.add(new_build)

        backend = self.get_backend()
        backend.create_build(new_build)

        queue.delay('sync_build', kwargs={
            'build_id': new_build.id.hex,
        })

        context = {
            'build': {
                'id': new_build.id.hex,
                'link': '/builds/{0}/'.format(new_build.id.hex),
            },
        }

        return self.respond(context)
