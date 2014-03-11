from changes.api.base import APIView
from changes.models import TestGroup, TestCase


class TestGroupDetailsAPIView(APIView):
    def get(self, testgroup_id):
        testgroup = TestGroup.query.get(testgroup_id)
        if testgroup is None:
            return '', 404

        child_testgroups = list(TestGroup.query.filter(
            TestGroup.parent_id == testgroup.id,
        ))
        for tg in child_testgroups:
            tg.parent = testgroup

        if child_testgroups:
            test_case = None
        else:
            # we make the assumption that if theres no child testgroups, then
            # there should be a single test case
            test_case = TestCase.query.filter(
                TestCase.groups.contains(testgroup),
            ).first()

        # O(N) db calls, so dont abuse it
        context = []
        parent = testgroup
        while parent:
            context.append(parent)
            parent = parent.parent
        context.reverse()

        data = self.serialize(testgroup)

        data.update(self.serialize({
            'childTestGroups': child_testgroups,
            'context': context,
            'testCase': test_case,
        }))

        return self.respond(data, serialize=False)
