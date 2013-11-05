from changes.constants import Status
from changes.config import db
from changes.models import TestSuite, TestCase
from changes.testutils import APITestCase


class TestDetailsTest(APITestCase):
    def test_retrieve(self):
        older_build = self.create_build(self.project, status=Status.finished)
        older_suite = TestSuite(
            project=self.project,
            build=older_build,
            name='other',
        )
        db.session.add(older_suite)
        older_test = TestCase(
            project=self.project,
            build=older_build,
            suite_id=older_suite.id,
            package='TestDetailsTest',
            name='test_retrieve',
        )
        db.session.add(older_test)

        old_build = self.create_build(self.project, status=Status.finished)
        old_suite = TestSuite(
            project=self.project,
            build=old_build,
            name='default',
        )
        db.session.add(old_suite)
        old_test = TestCase(
            project=self.project,
            build=old_build,
            suite_id=old_suite.id,
            package='TestDetailsTest',
            name='test_retrieve',
        )
        db.session.add(old_test)

        build = self.create_build(self.project)
        suite = TestSuite(
            project=self.project,
            build=build,
            name='default',
        )
        db.session.add(suite)
        test = TestCase(
            project=self.project,
            build=build,
            suite_id=suite.id,
            package='TestDetailsTest',
            name='test_retrieve',
        )
        db.session.add(test)

        path = '/api/0/tests/{0}/'.format(
            test.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['test']['id'] == test.id.hex
        assert data['firstRun']['id'] == old_test.id.hex
        assert len(data['previousRuns']) == 1
        assert data['previousRuns'][0]['id'] == old_test.id.hex
