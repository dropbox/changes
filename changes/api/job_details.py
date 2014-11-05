from __future__ import absolute_import

from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.api.serializer.models.testcase import TestCaseWithOriginSerializer
from changes.constants import Result
from changes.models import Job, TestCase, LogSource
from changes.utils.originfinder import find_failure_origins


class JobDetailsAPIView(APIView):
    def get(self, job_id):
        job = Job.query.options(
            joinedload('project', innerjoin=True),
        ).get(job_id)
        if job is None:
            return '', 404

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
            'testFailures': {
                'total': num_test_failures,
                'tests': self.serialize(test_failures, extended_serializers),
            },
            'logs': log_sources,
        })

        return self.respond(context)
