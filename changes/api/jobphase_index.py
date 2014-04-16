from __future__ import absolute_import

from sqlalchemy.orm import joinedload, subqueryload_all

from changes.api.base import APIView
from changes.models import Job, JobPhase, JobStep


class JobPhaseIndexAPIView(APIView):
    def get(self, job_id):
        job = Job.query.options(
            subqueryload_all(Job.phases),
            joinedload('project', innerjoin=True),
        ).get(job_id)
        if job is None:
            return '', 404

        phase_list = list(JobPhase.query.options(
            subqueryload_all(JobPhase.steps, JobStep.node),
            subqueryload_all(JobPhase.steps, JobStep.logsources)
        ).filter(
            JobPhase.job_id == job.id,
        ).order_by(JobPhase.date_started.asc(), JobPhase.date_created.asc()))

        context = []
        for phase, phase_data in zip(phase_list, self.serialize(phase_list)):
            phase_data['steps'] = []
            for step, step_data in zip(phase.steps, self.serialize(list(phase.steps))):
                step_data['logSources'] = self.serialize(list(step.logsources))
                phase_data['steps'].append(step_data)
            context.append(phase_data)

        return self.respond(context, serialize=False)

    def get_stream_channels(self, job_id):
        return [
            'jobs:{0}'.format(job_id),
            'testgroups:{0}:*'.format(job_id),
            'logsources:{0}:*'.format(job_id),
        ]
