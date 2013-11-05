from flask import Response

from changes.api.base import APIView
from changes.constants import Result
from changes.models import TestGroup, TestCase


class TestGroupDetailsAPIView(APIView):
    def get(self, testgroup_id):
        testgroup = TestGroup.query.get(testgroup_id)
        if testgroup is None:
            return Response(status=404)

        child_testgroups = list(TestGroup.query.filter_by(
            parent_id=testgroup.id,
        ))

        test_failures = TestCase.query.filter(
            TestCase.groups.contains(testgroup),
            TestCase.result == Result.failed,
        ).order_by(
            TestCase.result.desc(), TestCase.duration.desc()
        )

        num_test_failures = test_failures.count()
        test_failures = test_failures[:25]

        context = {
            'build': testgroup.build,
            'testGroup': testgroup,
            'childTestGroups': child_testgroups,
            'testFailures': {
                'total': num_test_failures,
                'tests': test_failures,
            },
        }

        return self.respond(context)
