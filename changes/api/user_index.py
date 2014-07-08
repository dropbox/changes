from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse
from sqlalchemy.sql import func

from changes.api.base import APIView
from changes.models import User

ADMIN_CHOICES = ('0', '1')

SORT_CHOICES = ('email', 'date')


class UserIndexAPIView(APIView):
    get_parser = reqparse.RequestParser()
    get_parser.add_argument('query', type=unicode, location='args')
    get_parser.add_argument('is_admin', type=lambda x: bool(int(x)), location='args',
                            choices=ADMIN_CHOICES)
    get_parser.add_argument('sort', type=unicode, location='args',
                            choices=SORT_CHOICES, default='email')

    def get(self):
        args = self.get_parser.parse_args()

        queryset = User.query

        if args.query:
            queryset = queryset.filter(
                func.lower(User.email).contains(args.query.lower()),
            )

        if args.is_admin is not None:
            queryset = queryset.filter(
                User.is_admin == args.is_admin
            )

        if args.sort == 'email':
            queryset = queryset.order_by(User.email.asc())
        elif args.sort == 'date':
            queryset = queryset.order_by(User.date_created.asc())

        return self.paginate(queryset)
