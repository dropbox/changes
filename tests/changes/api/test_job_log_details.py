from changes.config import db
from changes.models import LogSource, LogChunk
from changes.testutils import APITestCase


class JobLogDetailsTest(APITestCase):
    def test_simple(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        source = LogSource(job=job, project=project, name='test')
        db.session.add(source)

        lc1 = LogChunk(
            job=job, project=project, source=source,
            offset=0, size=100, text='a' * 100,
        )
        db.session.add(lc1)
        lc2 = LogChunk(
            job=job, project=project, source=source,
            offset=100, size=100, text='b' * 100,
        )
        db.session.add(lc2)
        db.session.commit()

        path = '/api/0/jobs/{0}/logs/{1}/'.format(
            job.id.hex, source.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['source']['id'] == source.id.hex
        assert data['nextOffset'] == 201
        assert len(data['chunks']) == 2
        assert data['chunks'][0]['text'] == lc1.text
        assert data['chunks'][1]['text'] == lc2.text

    def test_raw(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        source = LogSource(job=job, project=project, name='test')
        db.session.add(source)

        lc1 = LogChunk(
            job=job, project=project, source=source,
            offset=0, size=100, text='a' * 100,
        )
        db.session.add(lc1)
        lc2 = LogChunk(
            job=job, project=project, source=source,
            offset=100, size=100, text='b' * 100,
        )
        db.session.add(lc2)
        db.session.commit()

        path = '/api/0/jobs/{0}/logs/{1}/?raw=1'.format(
            job.id.hex, source.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        assert resp.headers['Content-Type'] == 'text/plain; charset=utf-8'
        assert resp.data == lc1.text + lc2.text
