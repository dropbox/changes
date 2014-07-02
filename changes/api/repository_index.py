from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse
from sqlalchemy.sql import func

from changes.api.base import APIView
from changes.api.auth import requires_auth
from changes.config import db
from changes.models import Repository, RepositoryBackend

BACKEND_CHOICES = ('git', 'hg', 'unknown')

SORT_CHOICES = ('url', 'date')


class RepositoryIndexAPIView(APIView):
    get_parser = reqparse.RequestParser()
    get_parser.add_argument('query', type=unicode, location='args')
    get_parser.add_argument('backend', type=unicode, location='args',
                            choices=BACKEND_CHOICES)
    get_parser.add_argument('sort', type=unicode, location='args',
                            choices=SORT_CHOICES, default='url')

    post_parser = reqparse.RequestParser()
    post_parser.add_argument('url', type=unicode, required=True)
    post_parser.add_argument('backend', choices=('git', 'hg', 'unknown'))

    def get(self):
        args = self.get_parser.parse_args()

        queryset = Repository.query

        if args.query:
            queryset = queryset.filter(
                func.lower(Repository.url).contains(args.query.lower()),
            )

        if args.backend:
            queryset = queryset.filter(
                Repository.backend == RepositoryBackend[args.backend]
            )

        if args.sort == 'url':
            queryset = queryset.order_by(Repository.url.asc())
        elif args.sort == 'date':
            queryset = queryset.order_by(Repository.date_created.asc())

        return self.paginate(queryset)

    @requires_auth
    def post(self):
        args = self.post_parser.parse_args()

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
