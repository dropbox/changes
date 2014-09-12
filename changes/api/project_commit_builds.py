from __future__ import absolute_import, division, unicode_literals

from sqlalchemy.orm import joinedload, contains_eager

from changes.api.base import APIView
from changes.models import Build, Project, Revision, Source


class ProjectCommitBuildsAPIView(APIView):
    def get(self, project_id, commit_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        repo = project.repository
        revision = Revision.query.options(
            joinedload('author'),
        ).filter(
            Revision.repository_id == repo.id,
            Revision.sha == commit_id,
        ).first()
        if not revision:
            return '', 404

        build_query = Build.query.options(
            joinedload('author'),
            contains_eager('source').joinedload('revision'),
        ).join(
            Source, Build.source_id == Source.id,
        ).filter(
            Build.project_id == project.id,
            Source.revision_sha == revision.sha,
            Source.patch == None,  # NOQA
        ).order_by(Build.date_created.desc())

        return self.paginate(build_query)
