from __future__ import absolute_import, division, unicode_literals

import json

from datetime import datetime
from flask.ext.restful import reqparse

from changes.api.base import APIView
from changes.api.auth import requires_admin
from changes.config import db
from changes.constants import IMPLEMENTATION_CHOICES
from changes.db.utils import create_or_update
from changes.models import ItemOption, Step, STEP_OPTIONS


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
            return {"message": "step not found"}, 404

        return self.respond(step)

    @requires_admin
    def post(self, step_id):
        step = Step.query.get(step_id)
        if step is None:
            return {"message": "step not found"}, 404

        args = self.parser.parse_args()

        if args.implementation is not None:
            step.implementation = args.implementation

        if args.data is not None:
            data = json.loads(args.data)
            if not isinstance(data, dict):
                return {"message": "data must be a JSON mapping"}, 400

            impl_cls = step.get_implementation(load=False)
            if impl_cls is None:
                return {"message": "unable to load build step implementation"}, 400

            try:
                impl_cls(**data)
            except Exception:
                return {"message": "unable to create build step mapping provided data"}, 400
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

        return self.serialize(step), 200

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

        return '', 200
