from __future__ import absolute_import

from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.models import JobStep


class JobStepDetailsAPIView(APIView):
    def get(self, step_id):
        jobstep = JobStep.query.options(
            joinedload('project', innerjoin=True),
        ).get(step_id)
        if jobstep is None:
            return '', 404

        context = self.serialize(jobstep)

        return self.respond(context)
