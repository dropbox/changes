from __future__ import absolute_import, division, unicode_literals

from flask import Response
from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.models import Project, Build


class ProjectBuildIndexAPIView(APIView):
    def get(self, project_id=None):
        project = Project.query.get(project_id)
        if not project:
            return Response(status=404)
        queryset = Build.query.options(
            joinedload(Build.project),
            joinedload(Build.author),
        ).filter_by(
            project=project,
        ).order_by(Build.date_created.desc(), Build.date_started.desc())

        build_list = list(queryset)[:25]

        context = {
            'builds': build_list,
        }

        return self.respond(context)

    def get_stream_channels(self, project_id=None):
        return ['projects:{0}:builds'.format(project_id)]
