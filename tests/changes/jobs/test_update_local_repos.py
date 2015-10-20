from __future__ import absolute_import

import mock

from changes.config import db
from changes.jobs.update_local_repos import update_local_repos
from changes.models import RepositoryBackend, RepositoryStatus
from changes.testutils import TestCase
from changes.vcs.base import CommandError, Vcs


class UpdateLocalReposTest(TestCase):
    @mock.patch('changes.models.Repository.get_vcs')
    def test_simple(self, get_vcs_backend):
        vcs_backend = mock.MagicMock(spec=Vcs)
        get_vcs_backend.return_value = vcs_backend
        vcs_backend.update = mock.Mock()

        num_active_repos = 2
        for i in range(num_active_repos):
            self.create_repo(backend=RepositoryBackend.git)

        inactive_repo = self.create_repo(backend=RepositoryBackend.git)
        inactive_repo.status = RepositoryStatus.inactive
        unknown_backend_repo = self.create_repo(backend=RepositoryBackend.unknown)
        unknown_backend_repo.get_vcs = lambda: None
        db.session.commit()

        update_local_repos()
        assert vcs_backend.update.call_count == num_active_repos

        # Even if an update fails, make sure we still try to update for each repo
        vcs_backend = mock.MagicMock(spec=Vcs)
        get_vcs_backend.return_value = vcs_backend
        vcs_backend.update = mock.Mock(side_effect=CommandError('xyz', 1))

        update_local_repos()
        assert vcs_backend.update.call_count == num_active_repos
