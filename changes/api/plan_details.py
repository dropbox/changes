from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse

from changes.api.auth import requires_admin
from changes.api.base import APIView
from changes.config import db
from changes.models import Plan, PlanStatus
import uuid

STATUS_CHOICES = ('active', 'inactive')


class PlanDetailsAPIView(APIView):
    post_parser = reqparse.RequestParser()
    post_parser.add_argument('name', type=unicode)
    post_parser.add_argument('status', choices=STATUS_CHOICES)
    post_parser.add_argument('snapshot_plan_id', type=unicode)

    def get(self, plan_id):
        plan = Plan.query.get(plan_id)
        if plan is None:
            return '', 404

        context = self.serialize(plan)
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

        if args.status:
            plan.status = PlanStatus[args.status]

        if args.snapshot_plan_id:
            # Use snapshot from another plan to allow sharing snapshots.
            #
            # TODO(jukka): Verify that the plans belong to the same project.
            #   We can't share plans between projects.
            plan.snapshot_plan_id = uuid.UUID(hex=args.snapshot_plan_id)

        db.session.commit()

        return self.respond(plan)
