from __future__ import absolute_import

import mock
import pytest

from changes.config import db
from changes.models import ProjectConfigError
from changes.vcs.base import Vcs, CommandError, InvalidDiffError
from changes.testutils import TestCase


class GetConfigTest(TestCase):
    def setUp(self):
        self.project = self.create_project()
        db.session.commit()
        super(GetConfigTest, self).setUp()

    def test_revision_not_found(self):
        def throw(*args, **kwargs):
            raise CommandError('test command', 128)
        fake_vcs = mock.Mock(spec=Vcs)
        fake_vcs.read_file.side_effect = throw
        with mock.patch('changes.models.Repository.get_vcs') as mocked:
            mocked.return_value = fake_vcs
            config = self.project.get_config('a' * 40)
        assert config == self.project._default_config

    def test_invalid_diff(self):
        fake_vcs = mock.Mock(spec=Vcs)
        fake_vcs.read_file.side_effect = InvalidDiffError
        with mock.patch('changes.models.Repository.get_vcs') as mocked:
            mocked.return_value = fake_vcs
            with pytest.raises(InvalidDiffError):
                self.project.get_config('a' * 40)

    def test_no_vcs(self):
        with mock.patch('changes.models.Repository.get_vcs') as mocked:
            mocked.return_value = None
            with pytest.raises(NotImplementedError):
                self.project.get_config('a' * 40)

    def test_malformed_config(self):
        fake_vcs = mock.Mock(spec=Vcs)
        fake_vcs.read_file.return_value = '{'
        with mock.patch('changes.models.Repository.get_vcs') as mocked:
            mocked.return_value = fake_vcs
            with pytest.raises(ProjectConfigError):
                self.project.get_config('a' * 40)

    def test_invalid_config(self):
        fake_vcs = mock.Mock(spec=Vcs)
        fake_vcs.read_file.return_value = '[]'
        with mock.patch('changes.models.Repository.get_vcs') as mocked:
            mocked.return_value = fake_vcs
            with pytest.raises(ProjectConfigError):
                self.project.get_config('a' * 40)

    def test_simple(self):
        self.project._default_config = {
            'default1': 1,
            'default2': 2,
        }
        fake_vcs = mock.Mock(spec=Vcs)
        fake_vcs.read_file.return_value = '''
            {
                "item": true
            }
        '''
        with mock.patch('changes.models.Repository.get_vcs') as mocked:
            mocked.return_value = fake_vcs
            config = self.project.get_config('a' * 40)
        assert config == {
            'item': True,
            'default1': 1,
            'default2': 2,
        }
