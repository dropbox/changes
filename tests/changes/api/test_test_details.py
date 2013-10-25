from changes.config import db
from changes.models import Test
from changes.testutils import APITestCase


class TestDetailsTest(APITestCase):
    def test_retrieve(self):
        build = self.create_build(self.project)
        test = Test(
            project=self.project,
            build=build,
            label_sha='a' * 40,
            group_sha='a' * 40,
            group='default',
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
