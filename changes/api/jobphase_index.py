from __future__ import absolute_import

from flask import request

from sqlalchemy.orm import joinedload, subqueryload_all
from sqlalchemy.sql import func

from changes.api.base import APIView
from changes.api.serializer.models.logsource import LogSourceWithoutStepCrumbler
from changes.constants import Result
from changes.models.job import Job
from changes.models.jobphase import JobPhase
from changes.models.jobstep import JobStep
from changes.models.log import LogSource
from changes.models.test import TestCase
from changes.config import db


class JobPhaseIndexAPIView(APIView):
    def get(self, job_id):
        get_test_counts = request.args.get('test_counts', False)

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

        test_counts = {}
        if get_test_counts:
            rows = list(db.session.query(
                TestCase.step_id,
                func.count()
            ).filter(
                TestCase.job_id == job.id,
                TestCase.result == Result.failed,
            ).group_by(TestCase.step_id))
            for row in rows:
                test_counts[row[0]] = row[1]

        logsource_registry = {LogSource: LogSourceWithoutStepCrumbler()}
        context = []
        for phase, phase_data in zip(phase_list, self.serialize(phase_list)):
            phase_data['steps'] = []
            for step, step_data in zip(phase.steps, self.serialize(list(phase.steps))):
                step_data['logSources'] = self.serialize(list(step.logsources), extended_registry=logsource_registry)
                if step.id in test_counts:
                    step_data['testFailures'] = test_counts[step.id]
                phase_data['steps'].append(step_data)
            context.append(phase_data)

        return self.respond(context, serialize=False)
