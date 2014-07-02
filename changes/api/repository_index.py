from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse

from changes.api.base import APIView
from changes.api.auth import requires_auth
from changes.config import db
from changes.models import Repository, RepositoryBackend


class RepositoryIndexAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('url', type=unicode, required=True)
    parser.add_argument('backend', choices=('git', 'hg', 'unknown'))

    def get(self):
        queryset = Repository.query.order_by(Repository.url.asc())

        return self.paginate(queryset)

    @requires_auth
    def post(self):
        args = self.parser.parse_args()

        match = Repository.query.filter(
            Repository.url == args.url,
        ).first()
        if match:
            return '{"error": "Repository with url %r already exists"}' % (args.url,), 400

        repo = Repository(
            url=args.url,
            backend=RepositoryBackend[args.backend],
        )
        db.session.add(repo)
        db.session.commit()

        return self.respond(repo)
