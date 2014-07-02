from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse

from changes.api.auth import requires_auth
from changes.api.base import APIView
from changes.config import db
from changes.models import Repository, RepositoryBackend


class RepositoryDetailsAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('url', type=unicode)
    parser.add_argument('backend', choices=('git', 'hg', 'unknown'))

    def get(self, repository_id):
        repo = Repository.query.get(repository_id)
        if repo is None:
            return '', 404

        return self.respond(repo)

    @requires_auth
    def post(self, repository_id):
        repo = Repository.query.get(repository_id)
        if repo is None:
            return '', 404

        args = self.parser.parse_args()

        if args.url:
            repo.url = args.url
        if args.backend:
            repo.backend = RepositoryBackend[args.backend]

        db.session.add(repo)

        return self.respond(repo)
