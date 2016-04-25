from __future__ import absolute_import

from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.api.serializer.models.testcase import TestCaseWithOriginCrumbler
from changes.constants import Result
from changes.config import db
from changes.models.job import Job
from changes.models.jobstep import JobStep
from changes.models.log import LogSource
from changes.models.test import TestCase
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
            TestCase: TestCaseWithOriginCrumbler(),
        }

        # Restricting to matching JobStep ids when querying LogSources
        # allows us to use the LogSource.step_id index, which makes
        # the query significantly faster.
        jobstep_ids = db.session.query(JobStep.id).filter(
            JobStep.job_id == job.id
        ).subquery()
        log_sources = list(LogSource.query.options(
            joinedload('step'),
        ).filter(
            LogSource.job_id == job.id,
            LogSource.project_id == job.project_id,
            LogSource.step_id.in_(jobstep_ids),
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
