from changes.models import Repository, RepositoryBackend
from changes.testutils import APITestCase


class RepositoryListTest(APITestCase):
    path = '/api/0/repositories/'

    def test_simple(self):
        repo_1 = self.create_repo(
            url='https://example.com/bar',
        )
        repo_2 = self.create_repo(
            url='https://example.com/foo',
        )

        resp = self.client.get(self.path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == repo_1.id.hex
        assert data[1]['id'] == repo_2.id.hex


class RepositoryCreateTest(APITestCase):
    path = '/api/0/repositories/'

    def test_simple(self):
        # without auth
        resp = self.client.post(self.path, data={
            'url': 'ssh://example.com/foo',
            'backend': 'git',
        })
        assert resp.status_code == 401

        self.login_default()

        resp = self.client.post(self.path, data={
            'url': 'ssh://example.com/foo',
            'backend': 'git',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['url'] == 'ssh://example.com/foo'

        assert Repository.query.filter(
            Repository.url == 'ssh://example.com/foo',
            Repository.backend == RepositoryBackend.git,
        ).first()
