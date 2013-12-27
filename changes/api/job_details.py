from __future__ import absolute_import

from flask import Response
from sqlalchemy.orm import joinedload, subqueryload_all

from changes.api.base import APIView
from changes.api.serializer.models.testgroup import TestGroupWithOriginSerializer
from changes.constants import Result, Status, NUM_PREVIOUS_RUNS
from changes.models import Job, TestGroup, LogSource
from changes.utils.originfinder import find_failure_origins


class JobDetailsAPIView(APIView):
    def get(self, job_id):
        job = Job.query.options(
            subqueryload_all(Job.phases),
            joinedload(Job.project),
            joinedload(Job.author),
        ).get(job_id)
        if job is None:
            return Response(status=404)

        previous_runs = Job.query.filter(
            Job.project == job.project,
            Job.date_created < job.date_created,
            Job.status == Status.finished,
            Job.id != job.id,
            Job.patch == None,  # NOQA
        ).order_by(Job.date_created.desc())[:NUM_PREVIOUS_RUNS]

        # find all parent groups (root trees)
        test_groups = sorted(TestGroup.query.options(
            joinedload('parent'),
        ).filter(
            TestGroup.job_id == job.id,
            TestGroup.parent_id == None,  # NOQA: we have to use == here
        ), key=lambda x: x.name)

        test_failures = TestGroup.query.options(
            joinedload('parent'),
        ).filter(
            TestGroup.job_id == job.id,
            TestGroup.result == Result.failed,
            TestGroup.num_leaves == 0,
        ).order_by(TestGroup.name.asc())
        num_test_failures = test_failures.count()
        test_failures = test_failures[:25]

        if test_failures:
            failure_origins = find_failure_origins(
                job, test_failures)
            for test_failure in test_failures:
                test_failure.origin = failure_origins.get(test_failure)

        extended_serializers = {
            TestGroup: TestGroupWithOriginSerializer(),
        }

        log_sources = list(LogSource.query.filter(
            LogSource.job_id == job.id,
        ).order_by(LogSource.date_created.asc()))

        context = {
            'project': job.project,
            'build': job,
            'phases': job.phases,
            'testFailures': {
                'total': num_test_failures,
                'testGroups': self.serialize(test_failures, extended_serializers),
            },
            'logs': log_sources,
            'testGroups': test_groups,
            'previousRuns': previous_runs,
        }

        return self.respond(context)

    def get_stream_channels(self, job_id):
        return [
            'jobs:*:{0}'.format(job_id),
            'testgroups:{0}:*'.format(job_id),
            'logsources:{0}:*'.format(job_id),
        ]
