from __future__ import absolute_import, division, unicode_literals

from changes.api.base import APIView
from changes.constants import Status
from changes.config import db
from changes.models import JobStep


class JobStepDeallocateAPIView(APIView):

    def post(self, step_id):
        to_deallocate = JobStep.query.get(step_id)

        if to_deallocate is None:
            return '', 404

        if to_deallocate.status != Status.allocated:
            return {
                "error": "Only {0} job steps may be deallocated.",
                "actual_status": to_deallocate.status.name
            }, 400

        to_deallocate.status = Status.pending_allocation
        db.session.add(to_deallocate)
        db.session.commit()

        return self.respond(to_deallocate)
