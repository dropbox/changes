from flask import Response

from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.api.serializer.models.testgroup import TestGroupWithBuildSerializer
from changes.constants import Status, NUM_PREVIOUS_RUNS
from changes.models import Job, TestGroup, TestCase


class TestGroupDetailsAPIView(APIView):
    def get(self, testgroup_id):
        testgroup = TestGroup.query.get(testgroup_id)
        if testgroup is None:
            return Response(status=404)

        child_testgroups = list(TestGroup.query.filter_by(
            parent_id=testgroup.id,
        ))
        for test_group in child_testgroups:
            test_group.parent = testgroup

        if child_testgroups:
            test_case = None
        else:
            # we make the assumption that if theres no child testgroups, then
            # there should be a single test case
            test_case = TestCase.query.filter(
                TestCase.groups.contains(testgroup),
            ).first()

        previous_runs = TestGroup.query.join(Job).options(
            joinedload('job'),
            joinedload('job.author'),
            joinedload('parent'),
        ).filter(
            TestGroup.name_sha == testgroup.name_sha,
            TestGroup.id != testgroup.id,
            Job.date_created < testgroup.job.date_created,
            Job.status == Status.finished,
            Job.patch == None,  # NOQA
        ).order_by(Job.date_created.desc())[:NUM_PREVIOUS_RUNS]

        extended_serializers = {
            TestGroup: TestGroupWithBuildSerializer(),
        }

        # O(N) db calls, so dont abuse it
        context = []
        parent = testgroup
        while parent:
            context.append(parent)
            parent = parent.parent
        context.reverse()

        context = {
            'project': testgroup.project,
            'build': testgroup.job,
            'testGroup': testgroup,
            'childTestGroups': child_testgroups,
            'context': context,
            'testCase': test_case,
            'previousRuns': self.serialize(previous_runs, extended_serializers),
        }

        return self.respond(context)
