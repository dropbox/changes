from changes.constants import Result
from changes.config import db
from changes.models import TestGroup, TestCase
from changes.testutils import APITestCase


class TestGroupDetailsTest(APITestCase):
    def test_simple(self):
        change = self.create_change(self.project)
        build = self.create_build(self.project, change=change)
        testgroup = TestGroup(
            name='test.group',
            build=build,
            project=build.project,
        )
        db.session.add(testgroup)
        child_testgroup = TestGroup(
            name='test.group.child',
            build=build,
            project=build.project,
            parent_id=testgroup.id,
        )
        db.session.add(child_testgroup)

        # a testgroup which shouldnt show up
        invalid_testgroup = TestGroup(
            name='test.group.child',
            build=build,
            project=build.project,
        )
        db.session.add(invalid_testgroup)

        testcase = TestCase(
            name='test_simple',
            build=build,
            project=build.project,
            result=Result.failed,
        )
        db.session.add(testcase)
        testgroup.testcases.append(testcase)
        db.session.add(testgroup)

        # a testcase which shouldnt show up due to result
        invalid_testcase = TestCase(
            name='test_simple',
            build=build,
            project=build.project,
            result=Result.passed,
        )
        db.session.add(invalid_testcase)
        testgroup.testcases.append(invalid_testcase)
        db.session.add(invalid_testcase)

        # a testcase which shouldnt show up due to no group
        invalid_testcase2 = TestCase(
            name='test_simple',
            build=build,
            project=build.project,
            result=Result.failed,
        )
        db.session.add(invalid_testcase2)

        path = '/api/0/testgroups/{0}/'.format(
            testgroup.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['testGroup']['id'] == testgroup.id.hex
        assert data['build']['id'] == build.id.hex
        assert len(data['childTestGroups']) == 1
        assert data['childTestGroups'][0]['id'] == child_testgroup.id.hex
