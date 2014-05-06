from __future__ import absolute_import, division, unicode_literals

from changes.api.base import APIView
from changes.models import Step


class StepDetailsAPIView(APIView):
    def get(self, step_id):
        step = Step.query.get(step_id)
        if step is None:
            return '', 404

        context = self.serialize(step)
        context['data'] = dict(step.data)
        context['implementation'] = step.implementation

        return self.respond(context, serialize=False)
