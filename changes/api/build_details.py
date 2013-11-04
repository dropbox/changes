from flask import Response
from sqlalchemy.orm import joinedload, subqueryload_all

from changes.api.base import APIView
from changes.constants import Result
from changes.models import Build, TestGroup, TestCase


class BuildDetailsAPIView(APIView):
    def get(self, build_id):
        build = Build.query.options(
            subqueryload_all(Build.phases),
            joinedload(Build.project),
            joinedload(Build.author),
        ).get(build_id)
        if build is None:
            return Response(status=404)

        # find all parent groups (root trees)
        test_groups = list(TestGroup.query.filter(
            TestGroup.build_id == build.id,
            TestGroup.parent_id == None,  # NOQA: we have to use == here
        ))

        test_failures = TestCase.query.filter(
            TestCase.build_id == build.id,
            TestCase.result == Result.failed,
        ).order_by(
            TestCase.result.desc(), TestCase.duration.desc()
        )
        num_test_failures = test_failures.count()
        test_failures = test_failures[:25]

        context = {
            'build': build,
            'phases': build.phases,
            'testFailures': {
                'total': num_test_failures,
                'tests': test_failures,
            },
            'testGroups': test_groups,
        }

        return self.respond(context)

    def get_stream_channels(self, build_id):
        return [
            'builds:*:{0}'.format(build_id),
            'tests:*:{0}:*'.format(build_id),
        ]
