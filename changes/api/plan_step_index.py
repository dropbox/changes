from __future__ import absolute_import, division, unicode_literals

import json

from copy import deepcopy
from flask.ext.restful import reqparse

from changes.api.auth import get_project_slug_from_plan_id, requires_project_admin
from changes.api.base import APIView, error
from changes.config import db
from changes.constants import IMPLEMENTATION_CHOICES
from changes.db.utils import create_or_update
from changes.models.option import ItemOption
from changes.models.plan import Plan
from changes.models.step import Step, STEP_OPTIONS


class PlanStepIndexAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('data', default='{}')
    parser.add_argument('implementation', choices=IMPLEMENTATION_CHOICES,
                        required=True)
    parser.add_argument('order', type=int, default=0)
    for name in STEP_OPTIONS.keys():
        parser.add_argument(name)

    def get(self, plan_id):
        plan = Plan.query.get(plan_id)
        if plan is None:
            return error("plan not found", http_code=404)

        return self.respond(list(plan.steps))

    @requires_project_admin(get_project_slug_from_plan_id)
    def post(self, plan_id):
        plan = Plan.query.get(plan_id)
        if plan is None:
            return error("plan not found", http_code=404)

        args = self.parser.parse_args()

        step = Step(
            plan=plan,
            order=args.order,
            implementation=args.implementation,
        )

        try:
            data = json.loads(args.data)
        except ValueError as e:
            db.session.rollback()
            return error("invalid JSON: %s" % e)
        if not isinstance(data, dict):
            db.session.rollback()
            return error("data must be a JSON mapping")

        impl_cls = step.get_implementation(load=False)
        if impl_cls is None:
            db.session.rollback()
            return error("unable to load build step implementation")

        try:
            # XXX(dcramer): It's important that we deepcopy data so any
            # mutations within the BuildStep don't propagate into the db
            impl_cls(**deepcopy(data))
        except Exception as exc:
            db.session.rollback()
            return error("unable to create build step provided data: %s" % exc)

        step.data = data
        step.order = args.order
        db.session.add(step)

        plan.date_modified = step.date_modified
        db.session.add(plan)

        for name in STEP_OPTIONS.keys():
            value = args.get(name)
            if value is None:
                continue

            create_or_update(ItemOption, where={
                'item_id': step.id,
                'name': name,
            }, values={
                'value': value,
            })

        return self.serialize(step), 201
