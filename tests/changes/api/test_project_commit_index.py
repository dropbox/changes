from uuid import uuid4

from changes.testutils import APITestCase


class ProjectCommitIndexTest(APITestCase):
    def test_simple(self):
        fake_project_id = uuid4()

        self.create_build(self.project)

        project = self.create_project()
        revision1 = self.create_revision(repository=project.repository)
        revision2 = self.create_revision(
            repository=project.repository, parents=[revision1.sha])

        self.create_build(project, revision_sha=revision1.sha)
        build = self.create_build(project, revision_sha=revision1.sha)

        path = '/api/0/projects/{0}/commits/'.format(fake_project_id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 404

        path = '/api/0/projects/{0}/commits/'.format(project.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data['commits']) == 2
        assert data['commits'][0]['id'] == revision2.sha
        assert data['commits'][0]['build'] is None
        assert data['commits'][1]['id'] == revision1.sha
        assert data['commits'][1]['build']['id'] == build.id.hex
