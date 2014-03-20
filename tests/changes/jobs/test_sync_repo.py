from __future__ import absolute_import

import mock

from datetime import datetime

from changes.config import db
from changes.jobs.sync_repo import sync_repo
from changes.models import Repository, RepositoryBackend
from changes.testutils import TestCase
from changes.vcs.base import Vcs, RevisionResult


class SyncRepoTest(TestCase):
    @mock.patch('changes.models.Repository.get_vcs')
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
            backend=RepositoryBackend.git)

        sync_repo(repo_id=repo.id.hex, task_id=repo.id.hex)

        get_vcs_backend.assert_called_once_with()
        vcs_backend.log.assert_any_call(parent=None)
        vcs_backend.log.assert_any_call(parent='a' * 40)

        db.session.expire_all()

        repo = Repository.query.get(repo.id)

        assert repo.last_update_attempt is not None
        assert repo.last_update is not None

        # build sync is abstracted via sync_with_builder
        vcs_backend.update.assert_called_once_with()

        # ensure signal is fired
        queue_delay.assert_any_call('sync_repo', kwargs={
            'repo_id': repo.id.hex,
            'task_id': repo.id.hex,
            'parent_task_id': None,
        }, countdown=5)

        queue_delay.assert_any_call('notify_revision_created', kwargs={
            'repository_id': repo.id.hex,
            'revision_sha': 'a' * 40,
        })
