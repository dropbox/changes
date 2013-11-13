from changes.config import db
from changes.models import LogSource, LogChunk
from changes.testutils import APITestCase


class LogDetailsTest(APITestCase):
    def test_simple(self):
        build = self.create_build(self.project)
        source = LogSource(build=build, project=self.project, name='test')
        db.session.add(source)

        lc1 = LogChunk(
            build=build, project=self.project, source=source,
            offset=0, size=100, text='a' * 100,
        )
        db.session.add(lc1)
        lc2 = LogChunk(
            build=build, project=self.project, source=source,
            offset=100, size=100, text='b' * 100,
        )
        db.session.add(lc2)

        path = '/api/0/builds/{0}/logs/{1}/'.format(
            build.id.hex, source.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['nextOffset'] == 200
        assert len(data['chunks']) == 2
        assert data['chunks'][0]['text'] == lc1.text
        assert data['chunks'][1]['text'] == lc2.text
