from __future__ import absolute_import, division, unicode_literals

from sqlalchemy.sql import func

from changes.api.base import APIView
from changes.constants import Status
from changes.config import db, redis
from changes.models import Build, Job, JobPlan, JobStep


class JobStepAllocateAPIView(APIView):
    def find_next_jobstep(self):
        # find projects with pending allocations
        project_list = [p for p, in db.session.query(
            JobStep.project_id,
        ).filter(
            JobStep.status == Status.pending_allocation,
        ).group_by(
            JobStep.project_id
        )]
        if not project_list:
            return None

        # TODO(dcramer): this should be configurably and handle more cases
        # than just 'active job' as that can be 1 step or 100 steps
        # find the total number of job steps in progress per project
        # hard limit of 10 active jobs per project
        unavail_projects = [
            p for p, c in
            db.session.query(
                Job.project_id, func.count(Job.project_id),
            ).filter(
                Job.status.in_([Status.allocated, Status.in_progress]),
                Job.project_id.in_(project_list),
            ).group_by(
                Job.project_id,
            )
            if c >= 10
        ]

        filters = [
            JobStep.status == Status.pending_allocation,
        ]
        if unavail_projects:
            filters.append(~JobStep.project_id.in_(unavail_projects))

        base_queryset = JobStep.query.join(
            Job, JobStep.job_id == Job.id,
        ).join(
            Build, Job.build_id == Build.id,
        ).order_by(Build.priority.desc(), JobStep.date_created.asc())

        # prioritize a job that's has already started
        existing = base_queryset.filter(
            Job.status.in_([Status.allocated, Status.in_progress]),
            *filters
        ).first()
        if existing:
            return existing

        # now allow any prioritized project, based on order
        existing = base_queryset.filter(
            *filters
        ).first()
        if existing:
            return existing

        # TODO(dcramer): we want to burst but not go too far. For now just
        # let burst
        return base_queryset.first()

    def post(self):
        try:
            with redis.lock('jobstep:allocate', nowait=True):
                to_allocate = self.find_next_jobstep()

                # Should 204, but flask/werkzeug throws StopIteration (bug!) for tests
                if to_allocate is None:
                    return self.respond([])

                to_allocate.status = Status.allocated
                db.session.add(to_allocate)
                db.session.flush()
        except redis.UnableToGetLock:
            return self.respond({"error": "Another allocation is in progress"}), 503
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
