from __future__ import absolute_import, division, unicode_literals

import json

from datetime import datetime
from flask.ext.restful import reqparse

from changes.api.base import APIView
from changes.api.auth import requires_auth
from changes.config import db
from changes.models import Step

IMPLEMENTATION_CHOICES = (
    'changes.buildsteps.dummy.DummyBuildStep',
    'changes.backends.jenkins.buildstep.JenkinsBuildStep',
    'changes.backends.jenkins.buildstep.JenkinsFactoryBuildStep',
    'changes.backends.jenkins.buildstep.JenkinsGenericBuildStep',
)


class StepDetailsAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('data')
    parser.add_argument('implementation', choices=IMPLEMENTATION_CHOICES)
    parser.add_argument('order', type=int, default=0)

    def get(self, step_id):
        step = Step.query.get(step_id)
        if step is None:
            return '', 404

        return self.respond(step)

    @requires_auth
    def post(self, step_id):
        step = Step.query.get(step_id)
        if step is None:
            return '', 404

        args = self.parser.parse_args()

        if args.implementation is not None:
            step.implementation = args.implementation

        if args.data is not None:
            data = json.loads(args.data)
            if not isinstance(data, dict):
                return '', 400

            impl_cls = step.get_implementation(load=False)

            try:
                impl_cls(**data)
            except Exception:
                return '', 400
            step.data = data

        if args.order is not None:
            step.order = args.order

        db.session.add(step)

        plan = step.plan
        plan.date_modified = datetime.utcnow()
        db.session.add(plan)

        db.session.commit()

        return self.serialize(step), 200
