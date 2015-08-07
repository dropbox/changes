import json
import mock

from changes.config import db
from changes.testutils import APITestCase


class KickSyncRepoTest(APITestCase):
    path = '/api/0/kick_sync_repo/'

    def setUp(self):
        self.repo = self.create_repo()
        db.session.commit()
        super(KickSyncRepoTest, self).setUp()

    def test_simple(self):
        with mock.patch('changes.api.kick_sync_repo.sync_repo.delay') as mocked:
            resp = self.client.post(self.path, data={
                'repository': self.repo.url,
            })
        assert resp.status_code == 200
        assert mocked.call_count == 1
        _, kwargs = mocked.call_args
        assert kwargs['repo_id'] == self.repo.id.hex
        assert kwargs['continuous'] is False

    def test_not_found(self):
        resp = self.client.post(self.path, data={
            'repository': 'git@doesnotexist.com',
        })
        assert resp.status_code == 400
        error = json.loads(resp.data)
        assert 'repository' in error['problems']
