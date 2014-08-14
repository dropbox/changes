from changes.testutils import APITestCase


class JobArtifactIndexTest(APITestCase):
    def test_simple(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)
        artifact_1 = self.create_artifact(jobstep, 'junit.xml')
        artifact_2 = self.create_artifact(jobstep, 'coverage.xml')

        path = '/api/0/jobs/{0}/artifacts/'.format(job.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == artifact_2.id.hex
        assert data[1]['id'] == artifact_1.id.hex
