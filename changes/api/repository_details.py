from __future__ import absolute_import, division, unicode_literals

from changes.api.base import APIView
from changes.models import Repository


class RepositoryDetailsAPIView(APIView):
    def get(self, repository_id):
        repo = Repository.query.get(repository_id)
        if repo is None:
            return '', 404

        return self.respond(repo)
