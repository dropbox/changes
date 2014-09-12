from __future__ import absolute_import, division, unicode_literals

from changes.api.base import APIView
from changes.models import Project, Revision


class ProjectCommitDetailsAPIView(APIView):
    def get(self, project_id, commit_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        repo = project.repository
        revision = Revision.query.outerjoin(
            'author',
        ).filter(
            Revision.repository_id == repo.id,
            Revision.sha == commit_id,
        ).first()
        if not revision:
            return '', 404

        context = self.serialize(revision)

        context.update({
            'repository': repo,
        })

        return self.respond(context)
