from __future__ import absolute_import, division, unicode_literals

from changes.api.base import APIView
from changes.models.project import Project
from changes.models.repository import Repository


class RepositoryProjectIndexAPIView(APIView):
    def get(self, repository_id):
        repo = Repository.query.get(repository_id)
        if repo is None:
            return '', 404

        queryset = Project.query.filter(
            Project.repository_id == repo.id,
        )

        return self.paginate(queryset)
