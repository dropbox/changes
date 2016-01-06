from __future__ import absolute_import

from datetime import datetime, timedelta

import mock

from changes.config import db
from changes.testutils import TestCase
from changes.utils.project_trigger import files_changed_should_trigger_project


class FilesChangedTest(TestCase):

    def setUp(self):
        self.project = self.create_project()
        self.revision = self.create_revision(
            repository=self.project.repository
        )
        self.patch = self.create_patch(
            repository=self.project.repository,
            parent_revision_sha=self.revision.sha,
        )
        db.session.commit()
        super(FilesChangedTest, self).setUp()

    def test_config_changed(self):
        assert files_changed_should_trigger_project(
            [self.project.get_config_path()],
            self.project,
            {},
            self.revision.sha,
        )

    def test_blacklist_all(self):
        with mock.patch('changes.models.Project.get_config') as mocked:
            mocked.return_value = {
                'build.file-blacklist': ['a', 'b', 'c']
            }
            assert not files_changed_should_trigger_project(
                ['a', 'b'],
                self.project,
                {},
                self.revision.sha,
            )
            (sha, diff, _), _ = mocked.call_args
            assert sha == self.revision.sha
            assert diff is None

    def test_blacklist_not_all(self):
        with mock.patch('changes.models.Project.get_config') as mocked:
            mocked.return_value = {
                'build.file-blacklist': ['b', 'c']
            }
            assert files_changed_should_trigger_project(
                ['a', 'b'],
                self.project,
                {},
                self.revision.sha,
            )
            (sha, diff, _), _ = mocked.call_args
            assert sha == self.revision.sha
            assert diff is None

    def test_whitelist_empty(self):
        with mock.patch('changes.models.Project.get_config') as mocked:
            mocked.return_value = {
                'build.file-blacklist': []
            }
            assert files_changed_should_trigger_project(
                ['a', 'b'],
                self.project,
                {},
                self.revision.sha,
            )
            (sha, diff, _), _ = mocked.call_args
            assert sha == self.revision.sha
            assert diff is None

    def test_whitelist_unmatched(self):
        with mock.patch('changes.models.Project.get_config') as mocked:
            mocked.return_value = {
                'build.file-blacklist': []
            }
            assert not files_changed_should_trigger_project(
                ['a', 'b'],
                self.project,
                {'build.file-whitelist': """
x
y/a.txt
z
"""},
                self.revision.sha,
            )
            (sha, diff, _), _ = mocked.call_args
            assert sha == self.revision.sha
            assert diff is None

    def test_whitelist_matched(self):
        with mock.patch('changes.models.Project.get_config') as mocked:
            mocked.return_value = {
                'build.file-blacklist': []
            }
            assert files_changed_should_trigger_project(
                ['a', 'b', 'y/a.txt'],
                self.project,
                {'build.file-whitelist': """
x
y/a.txt
z
"""},
                self.revision.sha,
            )
            (sha, diff, _), _ = mocked.call_args
            assert sha == self.revision.sha
            assert diff is None

    def test_with_diff(self):
        with mock.patch('changes.models.Project.get_config') as mocked:
            mocked.return_value = {
                'build.file-blacklist': []
            }
            assert files_changed_should_trigger_project(
                ['a', 'b', 'y/a.txt'],
                self.project,
                {},
                self.revision.sha,
                self.patch.diff,
            )
            (sha, diff, _), _ = mocked.call_args
            assert sha == self.revision.sha

    def test_with_no_skips(self):
        with mock.patch('changes.models.Project.get_config') as mocked:
            mocked.return_value = {
                'build.file-blacklist': [],
                'build.minimum-minutes-between-builds': 0,
            }
            assert files_changed_should_trigger_project(
                ['a', 'b'],
                self.project,
                {},
                self.revision.sha,
            )
            (sha, diff, _), _ = mocked.call_args
            assert sha == self.revision.sha
            assert diff is None

    def test_with_timed_skips(self):
        # No builds yet
        with mock.patch('changes.models.Project.get_config') as mocked:
            mocked.return_value = {
                'build.file-blacklist': [],
                'build.minimum-minutes-between-builds': 30,
            }
            assert files_changed_should_trigger_project(
                ['a', 'b'],
                self.project,
                {},
                self.revision.sha,
            )
            (sha, diff, _), _ = mocked.call_args
            assert sha == self.revision.sha
            assert diff is None

        # Stale build
        self.create_build(self.project, date_created=datetime.now() - timedelta(minutes=31))

        with mock.patch('changes.models.Project.get_config') as mocked:
            mocked.return_value = {
                'build.file-blacklist': [],
                'build.minimum-minutes-between-builds': 30,
            }
            assert files_changed_should_trigger_project(
                ['a', 'b'],
                self.project,
                {},
                self.revision.sha,
            )
            (sha, diff, _), _ = mocked.call_args
            assert sha == self.revision.sha
            assert diff is None

        # Create recent build
        self.create_build(self.project, date_created=datetime.now() - timedelta(minutes=29))

        # Should fail because of recently created build.
        with mock.patch('changes.models.Project.get_config') as mocked:
            mocked.return_value = {
                'build.file-blacklist': [],
                'build.minimum-minutes-between-builds': 30,
            }
            assert not files_changed_should_trigger_project(
                ['a', 'b'],
                self.project,
                {},
                self.revision.sha,
            )
            (sha, diff, _), _ = mocked.call_args
