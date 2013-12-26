import mock

from datetime import datetime
from uuid import uuid4

from changes.constants import Status
from changes.testutils import APITestCase
from changes.vcs.base import Vcs, RevisionResult


class ProjectCommitIndexTest(APITestCase):
    def test_simple(self):
        fake_project_id = uuid4()

        self.create_job(self.project)

        project = self.create_project()
        revision1 = self.create_revision(repository=project.repository)
        revision2 = self.create_revision(
            repository=project.repository, parents=[revision1.sha])

        self.create_job(project, revision_sha=revision1.sha)
        job = self.create_job(
            project, revision_sha=revision1.sha, status=Status.finished)

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
        assert data['commits'][1]['build']['id'] == job.id.hex

    @mock.patch('changes.models.Repository.get_vcs')
    def test_with_vcs(self, get_vcs):
        def log_results():
            yield RevisionResult(
                id='a' * 40,
                message='hello world',
                author='Foo <foo@example.com>',
                author_date=datetime(2013, 9, 19, 22, 15, 22),
            )
            yield RevisionResult(
                id='b' * 40,
                message='biz',
                author='Bar <bar@example.com>',
                author_date=datetime(2013, 9, 19, 22, 15, 21),
            )

        fake_vcs = mock.Mock(spec=Vcs)
        fake_vcs.log.return_value = log_results()

        get_vcs.return_value = fake_vcs

        self.create_job(self.project)

        project = self.create_project()

        self.create_job(
            project, revision_sha='b' * 40, status=Status.finished)
        job = self.create_job(
            project, revision_sha='b' * 40, status=Status.finished)

        path = '/api/0/projects/{0}/commits/'.format(project.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data['commits']) == 2
        assert data['commits'][0]['id'] == 'a' * 40
        assert data['commits'][0]['build'] is None
        assert data['commits'][1]['id'] == 'b' * 40
        assert data['commits'][1]['build']['id'] == job.id.hex
