from __future__ import absolute_import, division, unicode_literals

import json

from copy import deepcopy
from datetime import datetime
from flask.ext.restful import reqparse

from changes.api.base import APIView, error
from changes.api.auth import requires_admin
from changes.config import db
from changes.constants import IMPLEMENTATION_CHOICES
from changes.db.utils import create_or_update
from changes.models.option import ItemOption
from changes.models.step import Step, STEP_OPTIONS


class StepDetailsAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('data')
    parser.add_argument('implementation', choices=IMPLEMENTATION_CHOICES)
    parser.add_argument('order', type=int, default=0)
    for name in STEP_OPTIONS.keys():
        parser.add_argument(name)

    def get(self, step_id):
        step = Step.query.get(step_id)
        if step is None:
            return error("step not found", http_code=404)

        return self.respond(step)

    @requires_admin
    def post(self, step_id):
        step = Step.query.get(step_id)
        if step is None:
            return error("step not found", http_code=404)

        args = self.parser.parse_args()

        if args.implementation is not None:
            step.implementation = args.implementation

        if args.data is not None:
            try:
                data = json.loads(args.data)
            except ValueError as e:
                return error("invalid JSON: %s" % e)

            if not isinstance(data, dict):
                return error("data must be a JSON mapping")

            impl_cls = step.get_implementation(load=False)
            if impl_cls is None:
                return error("unable to load build step implementation")

            try:
                # XXX(dcramer): It's important that we deepcopy data so any
                # mutations within the BuildStep don't propagate into the db
                impl_cls(**deepcopy(data))
            except Exception as exc:
                return error("unable to create build step mapping provided data: %s" % exc)
            step.data = data

        if args.order is not None:
            step.order = args.order

        step.date_modified = datetime.utcnow()
        db.session.add(step)

        plan = step.plan
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

        db.session.commit()
        return self.respond(step)

    @requires_admin
    def delete(self, step_id):
        step = Step.query.get(step_id)
        if step is None:
            return '', 404

        ItemOption.query.filter(
            ItemOption.item_id == step.id
        ).delete(
            synchronize_session=False,
        )

        Step.query.filter(
            Step.id == step.id,
        ).delete(
            synchronize_session=False,
        )

        db.session.commit()

        return self.respond({})
