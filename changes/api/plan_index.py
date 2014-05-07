from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse

from changes.api.auth import requires_admin
from changes.api.base import APIView
from changes.config import db
from changes.models import Plan


class PlanIndexAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('name', required=True)

    def get(self):
        queryset = Plan.query.order_by(Plan.label.asc())
        return self.paginate(queryset)

    @requires_admin
    def post(self):
        args = self.parser.parse_args()

        plan = Plan(label=args.name)
        db.session.add(plan)

        return self.respond(plan)
