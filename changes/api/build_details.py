from __future__ import absolute_import

from flask import Response
from sqlalchemy.orm import joinedload, subqueryload_all

from changes.api.base import APIView
from changes.api.serializer.models.testgroup import TestGroupWithOriginSerializer
from changes.constants import Result, Status, NUM_PREVIOUS_RUNS
from changes.models import Build, TestGroup, LogSource
from changes.utils.originfinder import find_failure_origins


class BuildDetailsAPIView(APIView):
    def get(self, build_id):
        build = Build.query.options(
            subqueryload_all(Build.phases),
            joinedload(Build.project),
            joinedload(Build.author),
        ).get(build_id)
        if build is None:
            return Response(status=404)

        previous_runs = Build.query.filter(
            Build.project == build.project,
            Build.date_created < build.date_created,
            Build.status == Status.finished,
            Build.id != build.id,
            Build.patch == None,  # NOQA
        ).order_by(Build.date_created.desc())[:NUM_PREVIOUS_RUNS]

        # find all parent groups (root trees)
        test_groups = sorted(TestGroup.query.filter(
            TestGroup.build_id == build.id,
            TestGroup.parent_id == None,  # NOQA: we have to use == here
        ), key=lambda x: x.name)

        test_failures = TestGroup.query.filter(
            TestGroup.build_id == build.id,
            TestGroup.result == Result.failed,
            TestGroup.num_leaves == 0,
        ).order_by(TestGroup.name.asc())
        num_test_failures = test_failures.count()
        test_failures = test_failures[:25]

        if test_failures:
            failure_origins = find_failure_origins(
                build, test_failures, previous_runs)
            for test_failure in test_failures:
                test_failure.origin = failure_origins.get(test_failure)

        extended_serializers = {
            TestGroup: TestGroupWithOriginSerializer(),
        }

        log_sources = list(LogSource.query.filter(
            LogSource.build_id == build.id,
        ).order_by(LogSource.date_created.asc()))

        context = {
            'project': build.project,
            'build': build,
            'phases': build.phases,
            'testFailures': {
                'total': num_test_failures,
                'testGroups': self.serialize(test_failures, extended_serializers),
            },
            'logs': log_sources,
            'testGroups': test_groups,
            'previousRuns': previous_runs,
        }

        return self.respond(context)

    def get_stream_channels(self, build_id):
        return [
            'builds:*:{0}'.format(build_id),
            'testgroups:{0}:*'.format(build_id),
            'logsources:{0}:*'.format(build_id),
        ]
