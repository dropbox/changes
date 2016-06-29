from __future__ import absolute_import

import mock

from datetime import datetime

from changes.config import db
from changes.jobs.import_repo import import_repo
from changes.models.repository import Repository, RepositoryBackend, RepositoryStatus
from changes.testutils import TestCase
from changes.vcs.base import Vcs, RevisionResult


class ImportRepoTest(TestCase):
    @mock.patch('changes.models.repository.Repository.get_vcs')
    @mock.patch('changes.config.queue.delay')
    def test_simple(self, queue_delay, get_vcs_backend):
        vcs_backend = mock.MagicMock(spec=Vcs)

        def log(parent):
            if parent is None:
                yield RevisionResult(
                    id='a' * 40,
                    message='hello world!',
                    author='Example <foo@example.com>',
                    author_date=datetime(2013, 9, 19, 22, 15, 22),
                )

        get_vcs_backend.return_value = vcs_backend
        vcs_backend.log.side_effect = log

        repo = self.create_repo(
            backend=RepositoryBackend.git,
            status=RepositoryStatus.importing,
        )

        with mock.patch.object(import_repo, 'allow_absent_from_db', True):
            import_repo(repo_id=repo.id.hex, task_id=repo.id.hex)

        get_vcs_backend.assert_called_once_with()
        vcs_backend.log.assert_called_once_with(parent=None)

        db.session.expire_all()

        repo = Repository.query.get(repo.id)

        assert repo.last_update_attempt is not None
        assert repo.last_update is not None
        assert repo.status == RepositoryStatus.active

        # build sync is abstracted via sync_with_builder
        vcs_backend.update.assert_called_once_with()

        # ensure signal is fired
        queue_delay.assert_any_call('import_repo', kwargs={
            'repo_id': repo.id.hex,
            'task_id': repo.id.hex,
            'parent': 'a' * 40,
        })
