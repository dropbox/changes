from __future__ import absolute_import, division, unicode_literals

from changes.api.base import APIView
from changes.constants import Result, Status
from changes.config import db
from changes.jobs.sync_job_step import sync_job_step
from changes.models import JobStep


class JobStepDeallocateAPIView(APIView):

    def post(self, step_id):
        to_deallocate = JobStep.query.get(step_id)

        if to_deallocate is None:
            return '', 404

        if to_deallocate.status not in (Status.allocated, Status.in_progress):
            return {
                "error": "Only allocated and in_progress job steps may be deallocated.",
                "actual_status": to_deallocate.status.name
            }, 400

        to_deallocate.status = Status.pending_allocation
        to_deallocate.result = Result.unknown
        to_deallocate.date_started = None
        to_deallocate.date_finished = None

        db.session.add(to_deallocate)
        db.session.commit()

        sync_job_step.delay(
            step_id=to_deallocate.id.hex,
            task_id=to_deallocate.id.hex,
            parent_task_id=to_deallocate.job_id.hex,
        )

        return self.respond(to_deallocate)
