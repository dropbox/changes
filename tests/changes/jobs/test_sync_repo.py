from __future__ import absolute_import

import mock

from datetime import datetime

from changes.config import db
from changes.jobs.sync_repo import sync_repo, NUM_RECENT_COMMITS
from changes.models import Repository, RepositoryBackend
from changes.testutils import TestCase
from changes.vcs.base import Vcs, RevisionResult


class SyncRepoTest(TestCase):
    @mock.patch('changes.jobs.sync_repo.fire_signal')
    @mock.patch('changes.models.Repository.get_vcs')
    @mock.patch('changes.config.queue.delay')
    def test_simple(self, queue_delay, get_vcs_backend, mock_fire_signal):
        vcs_backend = mock.MagicMock(spec=Vcs)

        def log(parent, limit, first_parent):
            if parent is None:
                yield RevisionResult(
                    id='a' * 40,
                    message='hello world!',
                    author='Example <foo@example.com>',
                    author_date=datetime(2013, 9, 19, 22, 15, 22),
                    branches=['a']
                )

        get_vcs_backend.return_value = vcs_backend
        vcs_backend.log.side_effect = log

        repo = self.create_repo(
            backend=RepositoryBackend.git)

        with mock.patch.object(sync_repo, 'allow_absent_from_db', True):
            sync_repo(repo_id=repo.id.hex, task_id=repo.id.hex)

        get_vcs_backend.assert_called_once_with()
        vcs_backend.log.assert_any_call(parent=None, limit=NUM_RECENT_COMMITS, first_parent=False)

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
        }, countdown=20)

        mock_fire_signal.delay.assert_any_call(
            signal='revision.created',
            kwargs={
                'repository_id': repo.id.hex,
                'revision_sha': 'a' * 40,
            },
        )

    @mock.patch('changes.jobs.sync_repo.fire_signal')
    @mock.patch('changes.models.Repository.get_vcs')
    @mock.patch('changes.config.queue.delay')
    def test_with_existing_revision(self, queue_delay, get_vcs_backend, mock_fire_signal):
        """
        Ensure that sync_repo creates and fires signals for existing revisions
        only if we haven't done so before and there are branches.
        """
        vcs_backend = mock.MagicMock(spec=Vcs)
        get_vcs_backend.return_value = vcs_backend
        repo = self.create_repo(backend=RepositoryBackend.git)

        existing_revision_branch_changed = RevisionResult(
            id=str(3) * 40,
            message='latest commit',
            author='Example <foo@example.com>',
            author_date=datetime(2013, 9, 19, 22, 15, 22),
            branches=['b']
        )
        existing_revision_branch_changed.save(repo)
        existing_revision_branch_changed.branches = ['b', 'c']

        existing_revision = RevisionResult(
            id=str(4) * 40,
            message='latest commit',
            author='Example <foo@example.com>',
            author_date=datetime(2013, 9, 19, 22, 15, 22),
            branches=['b'],
        )
        r, _, _ = existing_revision.save(repo)
        r.date_created_signal = datetime.utcnow()
        db.session.commit()

        existing_revision_no_branches = RevisionResult(
            id=str(5) * 40,
            message='latest commit',
            author='Example <foo@example.com>',
            author_date=datetime(2013, 9, 19, 22, 15, 22),
            branches=[]
        )
        existing_revision_no_branches.save(repo)
        db.session.commit()

        def log(parent, limit, first_parent):
            yield existing_revision
            yield existing_revision_branch_changed
            yield existing_revision_no_branches
            for i in range(3):
                yield RevisionResult(
                    id=str(i) * 40,
                    message='commit number' + str(i),
                    author='Example <foo@example.com>',
                    author_date=datetime(2013, 9, 19, 22, 15, 22),
                    branches=['b']
                )

        vcs_backend.log.side_effect = log

        with mock.patch.object(sync_repo, 'allow_absent_from_db', True):
            sync_repo(repo_id=repo.id.hex, task_id=repo.id.hex)

        get_vcs_backend.assert_called_once_with()
        vcs_backend.log.assert_any_call(parent=None, limit=NUM_RECENT_COMMITS, first_parent=False)

        db.session.expire_all()

        repo = Repository.query.get(repo.id)

        assert repo.last_update_attempt is not None
        assert repo.last_update is not None

        for i in range(4):
            mock_fire_signal.delay.assert_any_call(
                signal='revision.created',
                kwargs={
                    'repository_id': repo.id.hex,
                    'revision_sha': str(i) * 40,
                },
            )

        assert mock_fire_signal.delay.call_count == 4

        # Now all the revisions have been handled.
        # Another call to sync_repo should do nothing.
        mock_fire_signal.delay.call_count = 0
        with mock.patch.object(sync_repo, 'allow_absent_from_db', True):
            sync_repo(repo_id=repo.id.hex, task_id=repo.id.hex)
        assert mock_fire_signal.delay.call_count == 0
