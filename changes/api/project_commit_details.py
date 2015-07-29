from __future__ import absolute_import, division, unicode_literals

from sqlalchemy.orm import joinedload
from sqlalchemy.orm.exc import MultipleResultsFound

from changes.api.base import APIView
from changes.models import Project, Revision


class ProjectCommitDetailsAPIView(APIView):
    def get(self, project_id, commit_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        repo = project.repository
        try:
            revision = Revision.get_by_sha_prefix_query(
                repo.id,
                commit_id,
            ).options(
                joinedload('author')
            ).scalar()
        except MultipleResultsFound:
            return '', 404
        else:
            if not revision:
                return '', 404

            context = self.serialize(revision)

            context.update({
                'repository': repo,
            })

            return self.respond(context)
