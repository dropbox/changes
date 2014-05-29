from __future__ import absolute_import

from sqlalchemy.orm import joinedload, subqueryload_all

from changes.api.base import APIView
from changes.api.serializer.models.testcase import TestCaseWithOriginSerializer
from changes.constants import Result, Status, NUM_PREVIOUS_RUNS
from changes.models import Job, TestCase, LogSource
from changes.utils.originfinder import find_failure_origins


class JobDetailsAPIView(APIView):
    def get(self, job_id):
        job = Job.query.options(
            subqueryload_all(Job.phases),
            joinedload('project', innerjoin=True),
        ).get(job_id)
        if job is None:
            return '', 404

        previous_runs = Job.query.filter(
            Job.project == job.project,
            Job.date_created < job.date_created,
            Job.status == Status.finished,
            Job.id != job.id,
        ).order_by(Job.date_created.desc())[:NUM_PREVIOUS_RUNS]

        test_failures = TestCase.query.filter(
            TestCase.job_id == job.id,
            TestCase.result == Result.failed,
        ).order_by(TestCase.name.asc())
        num_test_failures = test_failures.count()
        test_failures = test_failures[:25]

        if test_failures:
            failure_origins = find_failure_origins(
                job.build, test_failures)
            for test_failure in test_failures:
                test_failure.origin = failure_origins.get(test_failure)

        extended_serializers = {
            TestCase: TestCaseWithOriginSerializer(),
        }

        log_sources = list(LogSource.query.options(
            joinedload('step'),
        ).filter(
            LogSource.job_id == job.id,
        ).order_by(LogSource.date_created.asc()))

        context = self.serialize(job)
        context.update({
            'phases': job.phases,
            'testFailures': {
                'total': num_test_failures,
                'tests': self.serialize(test_failures, extended_serializers),
            },
            'logs': log_sources,
            'previousRuns': previous_runs,
        })

        return self.respond(context)

    def get_stream_channels(self, job_id):
        return [
            'jobs:{0}'.format(job_id),
            'testgroups:{0}:*'.format(job_id),
            'logsources:{0}:*'.format(job_id),
        ]
