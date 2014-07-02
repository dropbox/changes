from changes.testutils import APITestCase


class RepositoryDetailsTest(APITestCase):
    def test_simple(self):
        repo = self.create_repo(
            url='https://example.com/bar',
        )

        path = '/api/0/repositories/{0}/'.format(repo.id)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == repo.id.hex
        assert data['url'] == repo.url
