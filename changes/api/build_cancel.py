from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.config import db
from changes.constants import Result, Status
from changes.models import Build, JobPlan


class BuildCancelAPIView(APIView):
    def post(self, build_id):
        build = Build.query.options(
            joinedload('project', innerjoin=True),
            joinedload('author'),
            joinedload('source').joinedload('revision'),
        ).get(build_id)
        if build is None:
            return '', 404

        if build.status == Status.finished:
            return '', 204

        cancelled = []

        # find any active/pending jobs
        for job in filter(lambda x: x.status != Status.finished, build.jobs):
            # TODO(dcramer): we make an assumption that there is a single step
            jobplan, implementation = JobPlan.get_build_step_for_job(job_id=job.id)
            if not implementation:
                continue

            implementation.cancel(job=job)
            cancelled.append(job)

        if not cancelled:
            return '', 204

        build.status = Status.finished
        build.result = Result.aborted
        db.session.add(build)

        return self.respond(build)
