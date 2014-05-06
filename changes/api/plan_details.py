from __future__ import absolute_import, division, unicode_literals

from changes.api.base import APIView
from changes.models import Plan


class PlanDetailsAPIView(APIView):
    def get(self, plan_id):
        plan = Plan.query.get(plan_id)
        if plan is None:
            return '', 404

        context = self.serialize(plan)
        context['projects'] = list(plan.projects)
        context['steps'] = list(plan.steps)

        return self.respond(context)
