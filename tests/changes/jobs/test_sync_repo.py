from __future__ import absolute_import

import mock

from changes.jobs.sync_repo import sync_repo, get_vcs
from changes.models import Repository, RepositoryBackend
from changes.testutils import TestCase
from changes.vcs.base import Vcs


class GetVcsTest(TestCase):
    def test_git(self):
        from changes.vcs.git import GitVcs
        repo = Repository(
            url='http://example.com/git-repo',
            backend=RepositoryBackend.git,
        )
        result = get_vcs(repo)
        assert type(result) == GitVcs

    def test_hg(self):
        from changes.vcs.hg import MercurialVcs
        repo = Repository(
            url='http://example.com/git-repo',
            backend=RepositoryBackend.hg,
        )
        result = get_vcs(repo)
        assert type(result) == MercurialVcs

    def test_unknown(self):
        repo = Repository(
            url='http://example.com/git-repo',
            backend=RepositoryBackend.unknown,
        )
        result = get_vcs(repo)
        assert result is None


class SyncRepoTest(TestCase):
    @mock.patch('changes.jobs.sync_repo.get_vcs')
    @mock.patch('changes.jobs.sync_repo.queue.delay')
    def test_simple(self, queue_delay, get_vcs_backend):
        vcs_backend = mock.MagicMock(spec=Vcs)

        get_vcs_backend.return_value = vcs_backend

        repo = self.create_repo(
            backend=RepositoryBackend.git)

        sync_repo(repo.id.hex)

        get_vcs_backend.assert_called_once_with(repo)

        repo = Repository.query.get(repo.id)

        assert repo.last_update is not None
        assert repo.last_update_attempt is not None

        # build sync is abstracted via sync_with_builder
        vcs_backend.update.assert_called_once_with()

        # ensure signal is fired
        queue_delay.assert_called_once_with('sync_repo', kwargs={
            'repo_id': repo.id.hex,
        }, countdown=15)
