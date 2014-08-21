from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse

from changes.api.base import APIView
from changes.models import Repository


class RepositoryTreeIndexAPIView(APIView):
    """ The branches and trees available for the given repository.

    This is exposed as an API on the repository because in the future there may
    be related preferences that affect the behavior for associated trees.
    """
    TREE_ARGUMENT_NAME = 'tree'

    get_parser = reqparse.RequestParser()
    get_parser.add_argument(TREE_ARGUMENT_NAME, type=unicode, location='args',
                            case_sensitive=False)

    def get(self, repository_id):
        repo = Repository.query.get(repository_id)
        if repo is None:
            return '', 404

        vcs = repo.get_vcs()
        if not vcs:
            return {'error': 'Repository has no backend specified'}, 422

        # Fetch all the branches
        branch_names = vcs.get_known_branches()

        # Filter out any branches that don't match the tree query
        args = self.get_parser.parse_args()
        if args[RepositoryTreeIndexAPIView.TREE_ARGUMENT_NAME]:
            query = args[RepositoryTreeIndexAPIView.TREE_ARGUMENT_NAME].lower()
            branches = [{'name': branch_name} for branch_name in branch_names
                        if branch_name.lower().startswith(query)]
        else:
            branches = [{'name': branch_name} for branch_name in branch_names]

        return self.paginate(branches)
