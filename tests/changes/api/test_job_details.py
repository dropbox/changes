from changes.config import db
from changes.models.log import LogSource
from changes.testutils import APITestCase


class JobDetailsTest(APITestCase):
    def test_simple(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)

        ls1 = LogSource(step=jobstep, job=job, project=project, name='test')
        db.session.add(ls1)
        ls2 = LogSource(step=jobstep, job=job, project=project, name='test2')
        db.session.add(ls2)
        db.session.commit()

        path = '/api/0/jobs/{0}/'.format(job.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == job.id.hex
        assert len(data['logs']) == 2
        assert data['logs'][0]['id'] == ls1.id.hex
        assert data['logs'][1]['id'] == ls2.id.hex
