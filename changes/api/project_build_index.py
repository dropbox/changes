from __future__ import absolute_import, division, unicode_literals

from flask import Response, request
from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.constants import NUM_PREVIOUS_RUNS
from changes.models import Project, Build


class ProjectBuildIndexAPIView(APIView):
    def _get_project(self, project_id):
        project = Project.query.options(
            joinedload(Project.repository),
        ).filter_by(slug=project_id).first()
        if project is None:
            project = Project.query.options(
                joinedload(Project.repository),
            ).get(project_id)
        return project

    def get(self, project_id):
        project = self._get_project(project_id)
        if not project:
            return Response(status=404)

        include_patches = request.args.get('include_patches') or '1'

        queryset = Build.query.options(
            joinedload(Build.project),
            joinedload(Build.author),
        ).filter_by(
            project=project,
        ).order_by(Build.date_created.desc(), Build.date_started.desc())

        if include_patches == '0':
            queryset = queryset.filter(
                Build.patch == None,  # NOQA
            )

        build_list = list(queryset)[:NUM_PREVIOUS_RUNS]

        context = {
            'builds': build_list,
        }

        return self.respond(context)

    def get_stream_channels(self, project_id=None):
        project = self._get_project(project_id)
        if not project:
            return Response(status=404)
        return ['projects:{0}:builds'.format(project.id.hex)]
