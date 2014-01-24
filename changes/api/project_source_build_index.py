from __future__ import absolute_import, division, unicode_literals

from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.models import Build, Project, Source


class ProjectSourceBuildIndexAPIView(APIView):
    def _get_project(self, project_id):
        project = Project.query.options(
            joinedload(Project.repository),
        ).filter_by(slug=project_id).first()
        if project is None:
            project = Project.query.options(
                joinedload(Project.repository),
            ).get(project_id)
        return project

    def get(self, project_id, source_id):
        project = self._get_project(project_id)
        if not project:
            return '', 404

        repo = project.repository
        source = Source.query.filter(
            Source.id == source_id,
            Source.repository_id == repo.id,
        ).first()
        if source is None:
            return '', 404

        build_list = list(Build.query.options(
            joinedload('author'),
        ).filter(
            Build.source_id == source.id,
        ).order_by(Build.date_created.desc()))[:100]

        return self.respond(build_list)
