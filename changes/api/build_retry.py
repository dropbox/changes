from flask import Response
from sqlalchemy.orm import joinedload, subqueryload_all

from datetime import datetime

from changes.api.base import APIView
from changes.config import db, queue
from changes.constants import Cause, Status
from changes.models import Build, BuildPlan


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
            source=build.source,
            change=build.change,
            repository=build.repository,
            project=build.project,
            revision_sha=build.revision_sha,
            target=build.target,
            parent_id=build.id,
            patch=build.patch,
            label=build.label,
            status=Status.queued,
            message=build.message,
            # TODO(dcramer): author is a lie
            author=build.author,
            cause=Cause.retry,
        )
        db.session.add(new_build)

        buildplan = BuildPlan.query.filter(
            BuildPlan.build_id == build.id,
        ).first()
        if buildplan:
            new_build_plan = BuildPlan(
                project_id=build.project_id,
                build_id=new_build.id,
                plan_id=buildplan.plan_id,
                family_id=buildplan.family_id,
            )
            db.session.add(new_build_plan)

        # TODO: some of this logic is repeated from the create build endpoint
        if new_build.change:
            new_build.change.date_modified = datetime.utcnow()
            db.session.add(new_build.change)

        db.session.commit()

        queue.delay('create_build', kwargs={
            'build_id': new_build.id.hex,
        }, countdown=5)

        context = {
            'build': {
                'id': new_build.id.hex,
                'link': '/builds/{0}/'.format(new_build.id.hex),
            },
        }

        return self.respond(context)
