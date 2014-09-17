import urllib

from mock import patch

from changes.testutils import APITestCase
from changes.models import RepositoryBackend


class RepositoryTreeListTest(APITestCase):
    def test_no_vcs(self):
        repo = self.create_repo(url='https://example.co.nonexistent/bar')
        path = '/api/0/repositories/{0}/branches/'.format(repo.id)
        resp = self.client.get(path)
        self.assertEquals(resp.status_code, 422, resp.data)
        self.assertIn('backend', resp.data)

    @patch('changes.vcs.git.GitVcs.get_known_branches')
    def test_get_single_branch(self, known_branches_mock):
        test_branch_name = 'some_branch_name'
        known_branches_mock.return_value = [test_branch_name]
        repo = self.create_repo(url='https://example.co.nonexistent/bar',
                                backend=RepositoryBackend.git)
        path = '/api/0/repositories/{0}/branches/'.format(repo.id)

        resp = self.client.get(path)
        self.assertEquals(resp.status_code, 200, resp.data)
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['name'] == test_branch_name

    @patch('changes.vcs.git.GitVcs.get_known_branches')
    def test_get_multiple_branches(self, known_branches_mock):
        test_branches = ['first_branch', '2nd:Branch']
        known_branches_mock.return_value = test_branches
        repo = self.create_repo(url='https://example.co.nonexistent/bar',
                                backend=RepositoryBackend.git)
        path = '/api/0/repositories/{0}/branches/'.format(repo.id)

        resp = self.client.get(path)
        self.assertEquals(resp.status_code, 200, resp.data)
        data = self.unserialize(resp)
        assert len(data) == 2
        self.assertIn(data[0]['name'], test_branches)
        self.assertIn(data[1]['name'], test_branches)

    @patch('changes.vcs.git.GitVcs.get_known_branches')
    def test_get_with_tree_filter(self, known_branches_mock):
        test_branches = ['master', 'MATCH_ME']
        known_branches_mock.return_value = test_branches
        repo = self.create_repo(url='https://example.co.nonexistent/bar',
                                backend=RepositoryBackend.git)

        path = '/api/0/repositories/{0}/branches/?branch={1}'.format(
            repo.id, 'match')

        resp = self.client.get(path)
        self.assertEquals(resp.status_code, 200, resp.data)
        data = self.unserialize(resp)
        assert len(data) == 1
        self.assertIn(data[0]['name'], 'MATCH_ME')

    @patch('changes.vcs.git.GitVcs.get_known_branches')
    def test_get_with_escaped_tree_filter(self, known_branches_mock):
        test_branches = ['master', 'MATCH:/ME']
        known_branches_mock.return_value = test_branches
        repo = self.create_repo(url='https://example.co.nonexistent/bar',
                                backend=RepositoryBackend.git)

        path = '/api/0/repositories/{0}/branches/?branch={1}'.format(
            repo.id, urllib.quote('match:/', safe=''))

        resp = self.client.get(path)
        self.assertEquals(resp.status_code, 200, resp.data)
        data = self.unserialize(resp)
        assert len(data) == 1
        self.assertIn(data[0]['name'], 'MATCH:/ME')

    @patch('changes.vcs.git.GitVcs.get_known_branches')
    def test_get_with_caching(self, known_branches_mock):
        test_branches = ['first_branch', '2nd:Branch']
        known_branches_mock.return_value = test_branches
        repo = self.create_repo(url='https://example.co.nonexistent/bar',
                                backend=RepositoryBackend.git)
        path = '/api/0/repositories/{0}/branches/'.format(repo.id)

        # Get first time to warm up cache
        resp = self.client.get(path)
        self.assertEquals(resp.status_code, 200, resp.data)
        data = self.unserialize(resp)
        print(data)
        assert len(data) == 2

        # Get again to fetch from cache
        resp = self.client.get(path)
        self.assertEquals(resp.status_code, 200, resp.data)
        data = self.unserialize(resp)
        print(data)
        assert len(data) == 2
        self.assertIn(data[0]['name'], test_branches)
        self.assertIn(data[1]['name'], test_branches)
