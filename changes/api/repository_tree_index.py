from __future__ import absolute_import, division, unicode_literals

from changes.api.base import APIView
from changes.models import Repository


class RepositoryTreeIndexAPIView(APIView):
    """ The branches and trees available for the given repository.

    This is exposed as an API on the repository because in the future there may
    be related preferences that affect the behavior for associated trees.
    """
    def get(self, repository_id):
        repo = Repository.query.get(repository_id)
        if repo is None:
            return '', 404

        vcs = repo.get_vcs()
        if not vcs:
            return {'error': 'Repository has no backend specified'}, 422

        branch_name_list = vcs.get_known_branches()
        branches = [{'name': branch_name} for branch_name in branch_name_list]
        return self.paginate(branches)
