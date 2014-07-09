from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse

from changes.api.auth import requires_admin
from changes.api.base import APIView
from changes.config import db
from changes.models import Plan


class PlanDetailsAPIView(APIView):
    post_parser = reqparse.RequestParser()
    post_parser.add_argument('name', type=unicode)

    def get(self, plan_id):
        plan = Plan.query.get(plan_id)
        if plan is None:
            return '', 404

        context = self.serialize(plan)
        context['projects'] = list(plan.projects)
        context['steps'] = list(plan.steps)

        return self.respond(context)

    @requires_admin
    def post(self, plan_id):
        plan = Plan.query.get(plan_id)
        if plan is None:
            return '', 404

        args = self.post_parser.parse_args()

        if args.name:
            plan.label = args.name

        db.session.add(plan)
        db.session.commit()

        return self.respond(plan)
