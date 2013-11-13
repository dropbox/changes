from changes.config import db
from changes.models import LogSource
from changes.testutils import APITestCase


class BuildDetailsTest(APITestCase):
    def test_simple(self):
        change = self.create_change(self.project)
        build = self.create_build(self.project, change=change)

        ls1 = LogSource(build=build, project=self.project, name='test')
        db.session.add(ls1)
        ls2 = LogSource(build=build, project=self.project, name='test2')
        db.session.add(ls2)

        path = '/api/0/builds/{1}/'.format(
            change.id.hex, build.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['build']['id'] == build.id.hex
        assert len(data['logs']) == 2
        assert data['logs'][0]['id'] == ls1.id.hex
        assert data['logs'][1]['id'] == ls2.id.hex
