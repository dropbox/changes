from __future__ import absolute_import, division, unicode_literals

from datetime import datetime
from flask.ext.restful import reqparse

from changes.api.auth import requires_admin
from changes.api.base import APIView
from changes.config import db
from changes.models import Plan, Project


class PlanProjectIndexAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('id', required=True)

    def get(self, plan_id):
        plan = Plan.query.get(plan_id)
        if plan is None:
            return '', 404

        return self.respond(list(plan.projects))

    @requires_admin
    def post(self, plan_id):
        plan = Plan.query.get(plan_id)
        if plan is None:
            return '', 404

        args = self.parser.parse_args()

        project = Project.query.get(args.id)
        if project is None:
            return '', 400

        plan.projects.append(project)

        plan.date_modified = datetime.utcnow()
        db.session.add(plan)

        db.session.commit()

        return '', 200

    @requires_admin
    def delete(self, plan_id):
        plan = Plan.query.get(plan_id)
        if plan is None:
            return '', 404

        args = self.parser.parse_args()

        project = Project.query.get(args.id)
        if project is None:
            return '', 400

        plan.projects.remove(project)

        plan.date_modified = datetime.utcnow()
        db.session.add(plan)

        db.session.commit()

        return '', 200
