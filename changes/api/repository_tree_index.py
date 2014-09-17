from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse

from changes.api.base import APIView
from changes.models import Repository
from changes.config import redis

import json


class RepositoryTreeIndexAPIView(APIView):
    """ The branches and trees available for the given repository.

    This is exposed as an API on the repository because in the future there may
    be related preferences that affect the behavior for associated trees.
    """
    TREE_ARGUMENT_NAME = 'branch'
    BRANCH_CACHE_SECONDS = 30

    get_parser = reqparse.RequestParser()
    get_parser.add_argument(TREE_ARGUMENT_NAME, type=unicode, location='args',
                            case_sensitive=False)

    @staticmethod
    def get_redis_key(repository_id):
        return '%s:%s' % (repository_id,
                          RepositoryTreeIndexAPIView.TREE_ARGUMENT_NAME)

    def get(self, repository_id):
        repo = Repository.query.get(repository_id)
        if repo is None:
            return '', 404

        # Branches rarely change, so avoid making a call to the VCS if cached
        cache_key = RepositoryTreeIndexAPIView.get_redis_key(repository_id)
        cached_branches = redis.get(cache_key)
        if cached_branches:
            return self.respond(json.loads(cached_branches))

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

        # Cache response JSON for a short period of time
        redis.setex(cache_key, json.dumps(branches),
                    RepositoryTreeIndexAPIView.BRANCH_CACHE_SECONDS)

        return self.respond(branches)
