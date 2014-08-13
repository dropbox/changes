from changes.testutils import APITestCase


class RepositoryProjectListTest(APITestCase):
    def test_simple(self):
        repo = self.create_repo(url='https://example.com/bar')
        project = self.create_project(repository=repo, slug='foo')
        repo_2 = self.create_repo(url='https://example.com/foo')
        self.create_project(repository=repo_2, slug='bar')

        path = '/api/0/repositories/{0}/projects/'.format(repo.id)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == project.id.hex
