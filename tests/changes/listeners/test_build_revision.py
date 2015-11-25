from __future__ import absolute_import, print_function

import yaml

from datetime import datetime
from mock import Mock, patch
from uuid import uuid4

from changes.config import db
from changes.listeners.build_revision import revision_created_handler, CommitTrigger
from changes.models import Build, ProjectOption
from changes.testutils.cases import TestCase
from changes.testutils.fixtures import SAMPLE_DIFF
from changes.vcs.base import CommandError, RevisionResult, Vcs, UnknownRevision


class RevisionCreatedHandlerTestCase(TestCase):

    def get_fake_vcs(self, log_results=None):
        def _log_results(parent=None, branch=None, offset=0, limit=1):
            assert not branch
            return iter([
                RevisionResult(
                    id='a' * 40,
                    message='hello world',
                    author='Foo <foo@example.com>',
                    author_date=datetime.utcnow(),
                )])
        if log_results is None:
            log_results = _log_results
        # Fake having a VCS and stub the returned commit log
        fake_vcs = Mock(spec=Vcs)
        fake_vcs.read_file.side_effect = CommandError(cmd="test command", retcode=128)
        fake_vcs.exists.return_value = True
        fake_vcs.log.side_effect = UnknownRevision(cmd="test command", retcode=128)
        fake_vcs.export.side_effect = UnknownRevision(cmd="test command", retcode=128)
        fake_vcs.get_changed_files.side_effect = UnknownRevision(cmd="test command", retcode=128)

        def fake_update():
            # this simulates the effect of calling update() on a repo,
            # mainly that `export` and `log` now works.
            fake_vcs.log.side_effect = log_results
            fake_vcs.export.side_effect = None
            fake_vcs.export.return_value = SAMPLE_DIFF
            fake_vcs.get_changed_files.side_effect = lambda id: Vcs.get_changed_files(fake_vcs, id)

        fake_vcs.update.side_effect = fake_update

        return fake_vcs

    @patch('changes.models.Repository.get_vcs')
    def test_simple(self, get_vcs):
        repo = self.create_repo()
        revision = self.create_revision(repository=repo)
        project = self.create_project(repository=repo)
        self.create_plan(project)

        get_vcs.return_value = self.get_fake_vcs()

        revision_created_handler(revision_sha=revision.sha, repository_id=repo.id)

        build_list = list(Build.query.filter(
            Build.project == project,
        ))

        assert len(build_list) == 1

    @patch('changes.models.Repository.get_vcs')
    def test_disabled(self, get_vcs):
        repo = self.create_repo()
        revision = self.create_revision(repository=repo)
        project = self.create_project(repository=repo)
        self.create_plan(project)

        get_vcs.return_value = self.get_fake_vcs()

        db.session.add(ProjectOption(project=project, name='build.commit-trigger', value='0'))
        db.session.flush()

        revision_created_handler(revision_sha=revision.sha, repository_id=repo.id)

        assert not Build.query.first()

    @patch('changes.models.Repository.get_vcs')
    @patch('changes.api.build_index.identify_revision')
    def test_file_whitelist(self, mock_identify_revision, mock_get_vcs):
        repo = self.create_repo()
        revision = self.create_revision(repository=repo)
        project = self.create_project(repository=repo)
        self.create_plan(project)

        option = ProjectOption(project=project, name='build.file-whitelist', value='foo.txt')

        mock_vcs = self.get_fake_vcs()
        mock_vcs.export.side_effect = None
        mock_vcs.export.return_value = SAMPLE_DIFF
        mock_vcs.get_changed_files.side_effect = lambda id: Vcs.get_changed_files(mock_vcs, id)
        mock_vcs.update.side_effect = None
        mock_identify_revision.return_value = revision
        mock_get_vcs.return_value = mock_vcs

        db.session.add(option)
        db.session.flush()

        revision_created_handler(revision_sha=revision.sha, repository_id=repo.id)

        mock_vcs.export.assert_called_once_with(revision.sha)

        assert not Build.query.first()

        option.value = 'ci/*'
        db.session.add(option)
        db.session.flush()

        revision_created_handler(revision_sha=revision.sha, repository_id=repo.id)

        mock_identify_revision.assert_called_once_with(repo, revision.sha)

        assert Build.query.first()

    @patch('changes.models.Repository.get_vcs')
    @patch('changes.api.build_index.identify_revision')
    def test_file_blacklist(self, mock_identify_revision, mock_get_vcs):
        repo = self.create_repo()
        revision = self.create_revision(repository=repo)
        project = self.create_project(repository=repo)
        self.create_plan(project)

        mock_vcs = self.get_fake_vcs()
        mock_vcs.export.side_effect = None
        mock_vcs.export.return_value = SAMPLE_DIFF
        mock_vcs.get_changed_files.side_effect = lambda id: Vcs.get_changed_files(mock_vcs, id)
        mock_vcs.update.side_effect = None
        mock_identify_revision.return_value = revision
        mock_vcs.read_file.side_effect = None
        mock_vcs.read_file.return_value = yaml.safe_dump({
            'build.file-blacklist': ['ci/*'],
        })
        mock_get_vcs.return_value = mock_vcs

        revision_created_handler(revision_sha=revision.sha, repository_id=repo.id)

        mock_vcs.export.assert_called_once_with(revision.sha)

        assert not Build.query.first()

        mock_vcs.read_file.return_value = yaml.safe_dump({
            'build.file-blacklist': ['ci/not-real'],
        })

        revision_created_handler(revision_sha=revision.sha, repository_id=repo.id)

        mock_identify_revision.assert_called_once_with(repo, revision.sha)

        assert Build.query.first()

    @patch('changes.models.Repository.get_vcs')
    @patch('changes.api.build_index.identify_revision')
    def test_invalid_config(self, mock_identify_revision, mock_get_vcs):
        repo = self.create_repo()
        revision = self.create_revision(repository=repo)
        project = self.create_project(repository=repo)
        project2 = self.create_project(repository=repo)
        self.create_plan(project)
        self.create_plan(project2)

        mock_vcs = self.get_fake_vcs()
        mock_vcs.export.side_effect = None
        mock_vcs.export.return_value = SAMPLE_DIFF
        mock_vcs.get_changed_files.side_effect = lambda id: Vcs.get_changed_files(mock_vcs, id)
        mock_vcs.update.side_effect = None
        mock_identify_revision.return_value = revision
        mock_vcs.read_file.side_effect = ('{{invalid yaml}}', yaml.safe_dump({
            'build.file-blacklist': ['ci/not-real'],
        }))
        mock_get_vcs.return_value = mock_vcs

        revision_created_handler(revision_sha=revision.sha, repository_id=repo.id)

        mock_vcs.export.assert_called_once_with(revision.sha)

        assert len(list(Build.query)) == 2

    def test_get_changed_files_updates_vcs(self):
        repo = self.create_repo()
        sha = uuid4().hex
        revision = self.create_revision(repository=repo, sha=sha)

        # No updated needed.
        with patch.object(repo, 'get_vcs') as get_vcs:
            mock_vcs = self.get_fake_vcs()
            mock_vcs.export.side_effect = None
            mock_vcs.export.return_value = SAMPLE_DIFF
            mock_vcs.get_changed_files.side_effect = lambda id: Vcs.get_changed_files(mock_vcs, id)
            mock_vcs.update.side_effect = None
            get_vcs.return_value = mock_vcs
            ct = CommitTrigger(revision)
            ct.get_changed_files()
            self.assertEqual(list(mock_vcs.method_calls), [
                ('exists', (), {}),
                ('get_changed_files', (sha,), {}),
                ('export', (sha,), {}),
                ])

        # Successful update
        with patch.object(repo, 'get_vcs') as get_vcs:
            mock_vcs = self.get_fake_vcs()
            # Raise first time, work second time.
            mock_vcs.export.side_effect = (UnknownRevision("", 1), SAMPLE_DIFF)
            mock_vcs.get_changed_files.side_effect = lambda id: Vcs.get_changed_files(mock_vcs, id)
            mock_vcs.update.side_effect = None
            get_vcs.return_value = mock_vcs
            ct = CommitTrigger(revision)
            ct.get_changed_files()
            self.assertEqual(list(mock_vcs.method_calls), [
                ('exists', (), {}),
                ('get_changed_files', (sha,), {}),
                ('export', (sha,), {}),
                ('update', (), {}),
                ('get_changed_files', (sha,), {}),
                ('export', (sha,), {}),
                ])

        # Unsuccessful update
        with patch.object(repo, 'get_vcs') as get_vcs:
            mock_vcs = self.get_fake_vcs()
            mock_vcs.exists.return_value = True
            # Revision is always unknown.
            mock_vcs.export.side_effect = UnknownRevision("", 1)
            mock_vcs.get_changed_files.side_effect = lambda id: Vcs.get_changed_files(mock_vcs, id)
            mock_vcs.update.side_effect = None
            get_vcs.return_value = mock_vcs

            ct = CommitTrigger(revision)
            with self.assertRaises(UnknownRevision):
                ct.get_changed_files()
            self.assertEqual(list(mock_vcs.method_calls), [
                ('exists', (), {}),
                ('get_changed_files', (sha,), {}),
                ('export', (sha,), {}),
                ('update', (), {}),
                ('get_changed_files', (sha,), {}),
                ('export', (sha,), {}),
                ])
