from mock import patch

from changes.testutils import APITestCase
from changes.models import RepositoryBackend
from changes.api.repository_tree_index import RepositoryTreeIndexAPIView


class RepositoryTreeListTest(APITestCase):
    def test_no_vcs(self):
        repo = self.create_repo(url='https://example.co.nonexistent/bar')
        path = '/api/0/repositories/{0}/trees/'.format(repo.id)
        resp = self.client.get(path)
        self.assertEquals(resp.status_code, 422, resp.data)
        self.assertIn('backend', resp.data)

    @patch('changes.vcs.git.GitVcs.get_known_branches')
    def test_get_single_branch(self, git_vcs_mock):
        test_branch_name = 'some_branch_name'
        git_vcs_mock.return_value = [test_branch_name]
        repo = self.create_repo(url='https://example.co.nonexistent/bar',
                                backend=RepositoryBackend.git)
        path = '/api/0/repositories/{0}/trees/'.format(repo.id)

        resp = self.client.get(path)
        self.assertEquals(resp.status_code, 200, resp.data)
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['name'] == test_branch_name

    @patch('changes.vcs.git.GitVcs.get_known_branches')
    def test_get_multiple_branches(self, git_vcs_mock):
        test_branches = ['first_branch', '2nd:Branch']
        git_vcs_mock.return_value = test_branches
        repo = self.create_repo(url='https://example.co.nonexistent/bar',
                                backend=RepositoryBackend.git)
        path = '/api/0/repositories/{0}/trees/'.format(repo.id)

        resp = self.client.get(path)
        self.assertEquals(resp.status_code, 200, resp.data)
        data = self.unserialize(resp)
        assert len(data) == 2
        self.assertIn(data[0]['name'], test_branches)
        self.assertIn(data[1]['name'], test_branches)


    @patch('changes.vcs.git.GitVcs.get_known_branches')
    def test_get_with_tree_filter(self, git_vcs_mock):
        test_branches = ['master', 'MATCH_ME']
        git_vcs_mock.return_value = test_branches
        repo = self.create_repo(url='https://example.co.nonexistent/bar',
                                backend=RepositoryBackend.git)

        path = '/api/0/repositories/{0}/trees/?{1}={2}'.format(
            repo.id, RepositoryTreeIndexAPIView.TREE_ARGUMENT_NAME, 'match')

        resp = self.client.get(path)
        self.assertEquals(resp.status_code, 200, resp.data)
        data = self.unserialize(resp)
        assert len(data) == 1
        self.assertIn(data[0]['name'], 'MATCH_ME')
