from datetime import datetime

from changes.constants import Result, Status
from changes.config import db
from changes.models import TestCase
from changes.testutils import APITestCase


class TestGroupDetailsTest(APITestCase):
    def test_simple(self):
        previous_source = self.create_source(self.project)
        previous_build = self.create_build(
            project=self.project, source=previous_source,
            date_created=datetime(2013, 9, 19, 22, 15, 22))
        previous_job = self.create_job(
            build=previous_build, date_created=datetime(2013, 9, 19, 22, 15, 22),
            status=Status.finished)
        previous_testgroup = self.create_testgroup(
            job=previous_job, name='test.group')

        source = self.create_source(self.project)
        build = self.create_build(
            project=self.project, source=source,
            date_created=datetime(2013, 9, 19, 22, 15, 23))
        job = self.create_job(
            build=build, date_created=datetime(2013, 9, 19, 22, 15, 23),
            status=Status.finished)
        testgroup = self.create_testgroup(
            job=job, name='test.group')
        child_testgroup = self.create_testgroup(job, parent=testgroup)

        # a testgroup which shouldnt show up
        self.create_testgroup(job=job, name='test.group.child')

        testcase = TestCase(
            name='test_simple',
            job=job,
            project=job.project,
            result=Result.failed,
        )
        db.session.add(testcase)
        testgroup.testcases.append(testcase)
        db.session.add(testgroup)

        # a testcase which shouldnt show up due to result
        invalid_testcase = TestCase(
            name='test_simple',
            job=job,
            project=job.project,
            result=Result.passed,
        )
        db.session.add(invalid_testcase)
        testgroup.testcases.append(invalid_testcase)
        db.session.add(invalid_testcase)

        # a testcase which shouldnt show up due to no group
        invalid_testcase2 = TestCase(
            name='test_simple',
            job=job,
            project=job.project,
            result=Result.failed,
        )
        db.session.add(invalid_testcase2)

        path = '/api/0/testgroups/{0}/'.format(
            testgroup.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['testGroup']['id'] == testgroup.id.hex
        assert data['job']['id'] == job.id.hex
        assert data['build']['id'] == build.id.hex
        assert len(data['childTestGroups']) == 1
        assert data['childTestGroups'][0]['id'] == child_testgroup.id.hex
        assert data['previousRuns'][0]['id'] == previous_testgroup.id.hex
