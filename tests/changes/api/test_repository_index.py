from mock import patch

from changes.models import Repository, RepositoryBackend, RepositoryStatus
from changes.testutils import APITestCase


class RepositoryListTest(APITestCase):
    path = '/api/0/repositories/'

    def test_simple(self):
        repo_1 = self.create_repo(
            url='https://example.com/bar',
            status=RepositoryStatus.inactive,
        )
        repo_2 = self.create_repo(
            url='https://example.com/foo',
            status=RepositoryStatus.active,
        )

        resp = self.client.get(self.path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == repo_1.id.hex
        assert data[1]['id'] == repo_2.id.hex

        resp = self.client.get(self.path + '?status=active')
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == repo_2.id.hex


class RepositoryCreateTest(APITestCase):
    path = '/api/0/repositories/'

    @patch('changes.config.queue.delay')
    def test_simple(self, queue_delay):
        # without auth
        resp = self.client.post(self.path, data={
            'url': 'ssh://example.com/foo',
            'backend': 'git',
        })
        assert resp.status_code == 401

        self.login_default()

        # without admin
        resp = self.client.post(self.path, data={
            'url': 'ssh://example.com/foo',
            'backend': 'git',
        })
        assert resp.status_code == 403

        self.login_default_admin()

        resp = self.client.post(self.path, data={
            'url': 'ssh://example.com/foo',
            'backend': 'git',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['url'] == 'ssh://example.com/foo'

        repo = Repository.query.filter(
            Repository.url == 'ssh://example.com/foo',
        ).first()
        assert repo
        assert repo.backend == RepositoryBackend.git
        assert repo.status == RepositoryStatus.importing

        queue_delay.assert_called_once
