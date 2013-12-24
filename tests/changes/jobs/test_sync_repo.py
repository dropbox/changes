from __future__ import absolute_import

import mock

from changes.jobs.sync_repo import sync_repo
from changes.models import Repository, RepositoryBackend
from changes.testutils import TestCase
from changes.vcs.base import Vcs


class SyncRepoTest(TestCase):
    @mock.patch('changes.models.Repository.get_vcs')
    @mock.patch('changes.jobs.sync_repo.queue.delay')
    def test_simple(self, queue_delay, get_vcs_backend):
        vcs_backend = mock.MagicMock(spec=Vcs)

        get_vcs_backend.return_value = vcs_backend

        repo = self.create_repo(
            backend=RepositoryBackend.git)

        sync_repo(repo_id=repo.id.hex)

        get_vcs_backend.assert_called_once_with()

        repo = Repository.query.get(repo.id)

        assert repo.last_update is not None
        assert repo.last_update_attempt is not None

        # build sync is abstracted via sync_with_builder
        vcs_backend.update.assert_called_once_with()

        # ensure signal is fired
        queue_delay.assert_called_once_with('sync_repo', kwargs={
            'repo_id': repo.id.hex,
        }, countdown=15)
