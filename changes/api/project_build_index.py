from __future__ import absolute_import, division, unicode_literals

from flask import Response, request
from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.models import Project, Build


class ProjectBuildIndexAPIView(APIView):
    def get(self, project_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        include_patches = request.args.get('include_patches') or '1'

        queryset = Build.query.options(
            joinedload('project', innerjoin=True),
            joinedload('author'),
            joinedload('source'),
        ).filter(
            Build.project_id == project.id,
        ).order_by(Build.date_created.desc())

        if include_patches == '0':
            queryset = queryset.filter(
                Build.patch == None,  # NOQA
            )

        return self.paginate(queryset)

    def get_stream_channels(self, project_id=None):
        project = Project.get(project_id)
        if not project:
            return Response(status=404)
        return ['projects:{0}:builds'.format(project.id.hex)]
