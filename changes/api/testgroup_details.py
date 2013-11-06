from flask import Response

from changes.api.base import APIView
from changes.api.serializer.models.testgroup import TestGroupSerializer
from changes.constants import Result, Status, NUM_PREVIOUS_RUNS
from changes.models import Build, TestGroup, TestCase


class TestGroupWithBuildSerializer(TestGroupSerializer):
    def serialize(self, instance):
        data = super(TestGroupWithBuildSerializer, self).serialize(instance)
        data['build'] = instance.build
        return data


class TestGroupDetailsAPIView(APIView):
    def get(self, testgroup_id):
        testgroup = TestGroup.query.get(testgroup_id)
        if testgroup is None:
            return Response(status=404)

        child_testgroups = list(TestGroup.query.filter_by(
            parent_id=testgroup.id,
        ))

        if child_testgroups:
            tests = None
        else:
            tests = list(TestCase.query.filter(
                TestCase.groups.contains(testgroup),
            ).order_by(TestCase.duration.desc()))

        if tests:
            test_failures = filter(lambda x: x.result == Result.failed, tests)
            num_test_failures = len(test_failures)
        else:
            test_failures = TestCase.query.filter(
                TestCase.groups.contains(testgroup),
                TestCase.result == Result.failed,
            ).order_by(TestCase.duration.desc())

            num_test_failures = test_failures.count()
            test_failures = test_failures[:25]

        previous_runs = TestGroup.query.join(Build).filter(
            TestGroup.name_sha == testgroup.name_sha,
            Build.date_created < testgroup.build.date_created,
            Build.status == Status.finished,
            TestGroup.id != testgroup.id,
        ).order_by(Build.date_created.desc())[:NUM_PREVIOUS_RUNS]

        extended_serializers = {
            TestGroup: TestGroupWithBuildSerializer(),
        }

        context = {
            'build': testgroup.build,
            'testGroup': testgroup,
            'childTestGroups': child_testgroups,
            'testFailures': {
                'total': num_test_failures,
                'tests': test_failures,
            },
            'childTests': tests,
            'previousRuns': self.serialize(previous_runs, extended_serializers),
        }

        return self.respond(context)
