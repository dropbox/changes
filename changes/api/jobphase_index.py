from __future__ import absolute_import

from flask import Response
from sqlalchemy.orm import joinedload, subqueryload_all

from changes.api.base import APIView
from changes.api.serializer.models.jobphase import JobPhaseWithStepsSerializer
from changes.models import Job, JobPhase, JobStep


class JobPhaseIndexAPIView(APIView):
    def get(self, job_id):
        job = Job.query.options(
            subqueryload_all(Job.phases),
            joinedload(Job.project),
            joinedload(Job.author),
        ).get(job_id)
        if job is None:
            return Response(status=404)

        phase_list = list(JobPhase.query.options(
            subqueryload_all(JobPhase.steps, JobStep.node),
        ).filter(
            JobPhase.job_id == job.id,
        ).order_by(JobPhase.date_started.asc(), JobPhase.date_created.asc()))

        for phase in phase_list:
            phase.steps = sorted(
                phase.steps, key=lambda x: (x.date_started, x.date_created))

        return self.respond(self.serialize(phase_list, {
            JobPhase: JobPhaseWithStepsSerializer(),
        }))

    def get_stream_channels(self, job_id):
        return [
            'jobs:{0}'.format(job_id),
            'testgroups:{0}:*'.format(job_id),
            'logsources:{0}:*'.format(job_id),
        ]
