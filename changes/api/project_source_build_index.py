from __future__ import absolute_import, division, unicode_literals

from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.models import Build, Project, Source


class ProjectSourceBuildIndexAPIView(APIView):
    def get(self, project_id, source_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        repo = project.repository
        source = Source.query.filter(
            Source.id == source_id,
            Source.repository_id == repo.id,
        ).first()
        if source is None:
            return '', 404

        build_query = Build.query.options(
            joinedload('author'),
        ).filter(
            Build.project_id == project.id,
            Build.source_id == source.id,
        ).order_by(Build.date_created.desc())

        return self.paginate(build_query)
