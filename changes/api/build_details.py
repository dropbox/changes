from __future__ import absolute_import

from flask import Response
from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.constants import Status, NUM_PREVIOUS_RUNS
from changes.models import Build, Job


class BuildDetailsAPIView(APIView):
    def get(self, build_id):
        build = Build.query.options(
            joinedload(Build.project),
            joinedload(Build.author),
        ).get(build_id)
        if build is None:
            return Response(status=404)

        previous_runs = Build.query.filter(
            Build.project == build.project,
            Build.date_created < build.date_created,
            Build.status == Status.finished,
            Build.id != build.id,
            Build.patch == None,  # NOQA
        ).order_by(Build.date_created.desc())[:NUM_PREVIOUS_RUNS]

        jobs = list(Job.query.filter(
            Job.build_id == build.id,
        ))

        context = {
            'project': build.project,
            'build': build,
            'jobs': jobs,
            'previousRuns': previous_runs,
        }

        return self.respond(context)

    def get_stream_channels(self, build_id):
        return [
            'builds:{0}:jobs:*'.format(build_id),
        ]
