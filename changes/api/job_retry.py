from flask import Response
from sqlalchemy.orm import joinedload, subqueryload_all

from datetime import datetime

from changes.api.base import APIView
from changes.config import db, queue
from changes.constants import Cause, Status
from changes.models import Job, JobPlan


class JobRetryAPIView(APIView):
    def post(self, job_id):
        job = Job.query.options(
            subqueryload_all(Job.phases),
            joinedload(Job.project),
            joinedload(Job.author),
        ).get(job_id)
        if job is None:
            return Response(status=404)

        new_job = Job(
            source=job.source,
            change=job.change,
            build=job.build,
            repository=job.repository,
            project=job.project,
            revision_sha=job.revision_sha,
            target=job.target,
            parent_id=job.id,
            patch=job.patch,
            label=job.label,
            status=Status.queued,
            message=job.message,
            # TODO(dcramer): author is a lie
            author=job.author,
            cause=Cause.retry,
        )
        db.session.add(new_job)

        jobplan = JobPlan.query.filter(
            JobPlan.job_id == job.id,
        ).first()
        if jobplan:
            new_job_plan = JobPlan(
                project_id=job.project_id,
                job_id=new_job.id,
                plan_id=jobplan.plan_id,
                build_id=jobplan.build_id,
            )
            db.session.add(new_job_plan)

        # TODO: some of this logic is repeated from the create job endpoint
        if new_job.change:
            new_job.change.date_modified = datetime.utcnow()
            db.session.add(new_job.change)

        db.session.commit()

        queue.delay('create_job', kwargs={
            'job_id': new_job.id.hex,
        }, countdown=5)

        context = {
            'build': {
                'id': new_job.id.hex,
                'link': '/jobs/{0}/'.format(new_job.id.hex),
            },
        }

        return self.respond(context)
