from __future__ import absolute_import, division, unicode_literals

from flask import request
from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.models import Project, Build


class ProjectBuildSearchAPIView(APIView):
    def _get_project(self, project_id):
        project = Project.query.options(
            joinedload(Project.repository, innerjoin=True),
        ).filter_by(slug=project_id).first()
        if project is None:
            project = Project.query.options(
                joinedload(Project.repository),
            ).get(project_id)
        return project

    def get(self, project_id):
        project = self._get_project(project_id)
        if not project:
            return '', 404

        source = request.args.get('source')
        if not source:
            return '', 400

        queryset = Build.query.options(
            joinedload('project', innerjoin=True),
            joinedload('author'),
            joinedload('source'),
        ).filter(
            Build.target.startswith(source),
            Build.project_id == project.id,
        ).order_by(Build.date_created.desc())

        return self.paginate(queryset)
