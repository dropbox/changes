from __future__ import absolute_import, division, unicode_literals

import json

from flask.ext.restful import reqparse

from changes.api.auth import requires_admin
from changes.api.base import APIView
from changes.config import db
from changes.constants import IMPLEMENTATION_CHOICES
from changes.models import Step, Plan


class PlanStepIndexAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('data', default='{}')
    parser.add_argument('implementation', choices=IMPLEMENTATION_CHOICES,
                        required=True)
    parser.add_argument('order', type=int, default=0)

    def get(self, plan_id):
        plan = Plan.query.get(plan_id)
        if plan is None:
            return {"message": "plan not found"}, 404

        return self.respond(list(plan.steps))

    @requires_admin
    def post(self, plan_id):
        plan = Plan.query.get(plan_id)
        if plan is None:
            return {"message": "plan not found"}, 404

        args = self.parser.parse_args()

        step = Step(
            plan=plan,
            order=args.order,
            implementation=args.implementation,
        )

        data = json.loads(args.data)
        if not isinstance(data, dict):
            return {"message": "data must be a JSON mapping"}, 400

        impl_cls = step.get_implementation(load=False)
        if impl_cls is None:
            return {"message": "unable to load build step implementation"}, 400

        try:
            impl_cls(**data)
        except Exception:
            return {"message": "unable to create build step provided data"}, 400

        step.data = data
        step.order = args.order
        db.session.add(step)

        plan.date_modified = step.date_modified
        db.session.add(plan)

        db.session.commit()

        return self.serialize(step), 201
