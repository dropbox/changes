from __future__ import absolute_import, division, unicode_literals

from changes.api.base import APIView
from changes.constants import Status
from changes.config import db
from changes.models import JobPlan, JobStep


class JobStepAllocateAPIView(APIView):

    def post(self):
        to_allocate = JobStep.query.filter(
            JobStep.status == Status.pending_allocation,
        ).order_by(JobStep.date_created.desc()).first()

        # Should 204, but flask/werkzeug throws StopIteration (bug!) for tests
        if to_allocate is None:
            return self.respond([])

        to_allocate.status = Status.allocated
        db.session.add(to_allocate)
        db.session.commit()

        jobplan, buildstep = JobPlan.get_build_step_for_job(to_allocate.job_id)

        assert jobplan and buildstep

        context = self.serialize(to_allocate)
        context['project'] = self.serialize(to_allocate.project)
        context['resources'] = {
            'cpus': 4,
            'mem': 8 * 1024,
        }
        context['cmd'] = buildstep.get_allocation_command(to_allocate)

        return self.respond([context])
