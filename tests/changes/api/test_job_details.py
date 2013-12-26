from changes.config import db
from changes.models import LogSource
from changes.testutils import APITestCase


class JobDetailsTest(APITestCase):
    def test_simple(self):
        change = self.create_change(self.project)
        job = self.create_job(self.project, change=change)

        ls1 = LogSource(job=job, project=self.project, name='test')
        db.session.add(ls1)
        ls2 = LogSource(job=job, project=self.project, name='test2')
        db.session.add(ls2)

        path = '/api/0/jobs/{1}/'.format(
            change.id.hex, job.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['build']['id'] == job.id.hex
        assert len(data['logs']) == 2
        assert data['logs'][0]['id'] == ls1.id.hex
        assert data['logs'][1]['id'] == ls2.id.hex
