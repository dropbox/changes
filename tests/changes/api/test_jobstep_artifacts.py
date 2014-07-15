from cStringIO import StringIO

from changes.models import Artifact
from changes.testutils import APITestCase


class JobStepArtifactsCreateTest(APITestCase):
    def test_simple(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)

        path = '/api/0/jobsteps/{0}/artifacts/'.format(jobstep.id.hex)

        resp = self.client.post(path, data={
            'name': 'junit.xml',
            'file': (StringIO('hello world!\n'), 'junit.xml'),
        })

        assert resp.status_code == 201, resp.data
        data = self.unserialize(resp)
        artifact = Artifact.query.get(data['id'])
        assert artifact.name == 'junit.xml'
        assert artifact.file.filename.endswith('junit.xml')
