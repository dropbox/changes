from changes.config import db
from changes.models import TestSuite, TestCase
from changes.testutils import APITestCase


class TestDetailsTest(APITestCase):
    def test_retrieve(self):
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
