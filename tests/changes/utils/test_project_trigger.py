from __future__ import absolute_import

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
            (sha, _, diff), _ = mocked.call_args
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
            (sha, _, diff), _ = mocked.call_args
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
            (sha, _, diff), _ = mocked.call_args
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
            (sha, _, diff), _ = mocked.call_args
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
            (sha, _, diff), _ = mocked.call_args
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
            (sha, _, diff), _ = mocked.call_args
            assert sha == self.revision.sha
            assert diff == self.patch.diff
