from __future__ import absolute_import

from collections import defaultdict
from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.api.serializer.models.testgroup import TestGroupWithOriginSerializer
from changes.constants import Result, Status, NUM_PREVIOUS_RUNS
from changes.models import Build, Job, TestGroup, BuildSeen, User
from changes.utils.originfinder import find_failure_origins


class BuildDetailsAPIView(APIView):
    def get(self, build_id):
        build = Build.query.options(
            joinedload(Build.project),
            joinedload(Build.author),
        ).get(build_id)
        if build is None:
            return '', 404

        previous_runs = Build.query.filter(
            Build.project == build.project,
            Build.date_created < build.date_created,
            Build.status == Status.finished,
            Build.id != build.id,
            Build.patch == None,  # NOQA
        ).order_by(Build.date_created.desc())[:NUM_PREVIOUS_RUNS]

        jobs = list(Job.query.filter(
            Job.build_id == build.id,
        ))

        test_failures = TestGroup.query.options(
            joinedload('parent'),
            joinedload('job'),
        ).join(Job).filter(
            Job.build_id == build.id,
            TestGroup.job_id == Job.id,
            TestGroup.result == Result.failed,
            TestGroup.num_leaves == 0,
        ).order_by(TestGroup.name.asc())
        num_test_failures = test_failures.count()
        test_failures = test_failures[:25]

        failures_by_job = defaultdict(list)
        for failure in test_failures:
            failures_by_job[failure.job].append(failure)

        failure_origins = find_failure_origins(
            build, test_failures)
        for test_failure in test_failures:
            test_failure.origin = failure_origins.get(test_failure)

        seen_by = list(User.query.join(
            BuildSeen, BuildSeen.user_id == User.id,
        ).filter(
            BuildSeen.build_id == build.id,
        ))

        extended_serializers = {
            TestGroup: TestGroupWithOriginSerializer(),
        }

        context = {
            'project': build.project,
            'build': build,
            'jobs': jobs,
            'previousRuns': previous_runs,
            'seenBy': seen_by,
            'testFailures': {
                'total': num_test_failures,
                'testGroups': self.serialize(test_failures, extended_serializers),
            },
        }

        return self.respond(context)

    def get_stream_channels(self, build_id):
        return [
            'builds:{0}'.format(build_id),
            'builds:{0}:jobs'.format(build_id),
        ]
