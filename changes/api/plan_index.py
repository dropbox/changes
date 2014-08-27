from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse
from sqlalchemy.sql import func

from changes.api.auth import requires_admin
from changes.api.base import APIView
from changes.config import db
from changes.models import Plan, PlanStatus


SORT_CHOICES = ('name', 'date')

STATUS_CHOICES = ('', 'active', 'inactive')


class PlanIndexAPIView(APIView):
    get_parser = reqparse.RequestParser()
    get_parser.add_argument('query', type=unicode, location='args')
    get_parser.add_argument('sort', type=unicode, location='args',
                            choices=SORT_CHOICES, default='name')
    get_parser.add_argument('status', type=unicode, location='args',
                            choices=STATUS_CHOICES, default='active')

    post_parser = reqparse.RequestParser()
    post_parser.add_argument('name', required=True)

    def get(self):
        args = self.get_parser.parse_args()

        queryset = Plan.query

        if args.query:
            queryset = queryset.filter(
                func.lower(Plan.label).contains(args.query.lower()),
            )

        if args.status:
            queryset = queryset.filter(
                Plan.status == PlanStatus[args.status],
            )

        if args.sort == 'name':
            queryset = queryset.order_by(Plan.label.asc())
        elif args.sort == 'date':
            queryset = queryset.order_by(Plan.date_created.asc())

        return self.paginate(queryset)

    @requires_admin
    def post(self):
        args = self.post_parser.parse_args()

        plan = Plan(label=args.name)
        db.session.add(plan)

        return self.respond(plan)
