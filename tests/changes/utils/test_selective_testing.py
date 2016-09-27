import mock

from changes.constants import SelectiveTestingPolicy
from changes.models.project import ProjectConfigError, ProjectOptionsHelper
from changes.testutils.cases import TestCase
from changes.utils.selective_testing import get_selective_testing_policy
from changes.vcs.base import InvalidDiffError


class GetSelectiveTestingPolicyTestCase(TestCase):
    def test_enabled(self):
        project = self.create_project()
        with mock.patch.object(project, 'get_config') as mock_get_config:
            with mock.patch.object(ProjectOptionsHelper, 'get_whitelisted_paths') as mock_get_whitelisted_paths:
                mock_get_config.return_value = {
                    'build.file-blacklist': [],
                    'bazel.selective-testing-enabled': True,
                }
                mock_get_whitelisted_paths.return_value = []
                policy, messages = get_selective_testing_policy(project, 'a' * 40, diff='diff')
        mock_get_config.assert_called_once_with('a' * 40, 'diff')
        mock_get_whitelisted_paths.assert_called_once_with(project)
        assert len(messages) == 0
        assert policy is SelectiveTestingPolicy.enabled

    def test_get_config_error(self):
        project = self.create_project()
        with mock.patch.object(project, 'get_config') as mock_get_config:
            mock_get_config.side_effect = ProjectConfigError
            policy, messages = get_selective_testing_policy(project, 'a' * 40, diff='diff')
        mock_get_config.assert_called_once_with('a' * 40, 'diff')
        assert len(messages) > 0
        assert policy is SelectiveTestingPolicy.disabled

    def test_get_config_invalid_diff(self):
        project = self.create_project()
        with mock.patch.object(project, 'get_config') as mock_get_config:
            mock_get_config.side_effect = InvalidDiffError
            policy, messages = get_selective_testing_policy(project, 'a' * 40, diff='diff')
        mock_get_config.assert_called_once_with('a' * 40, 'diff')
        assert len(messages) > 0
        assert policy is SelectiveTestingPolicy.disabled

    def test_whitelist(self):
        project = self.create_project()
        with mock.patch.object(project, 'get_config') as mock_get_config:
            with mock.patch.object(ProjectOptionsHelper, 'get_whitelisted_paths') as mock_get_whitelisted_paths:
                mock_get_config.return_value = {
                    'build.file-blacklist': [],
                    'bazel.selective-testing-enabled': True,
                }
                mock_get_whitelisted_paths.return_value = ['a/a.txt']
                policy, messages = get_selective_testing_policy(project, 'a' * 40, diff='diff')
        mock_get_config.assert_called_once_with('a' * 40, 'diff')
        mock_get_whitelisted_paths.assert_called_once_with(project)
        assert len(messages) > 0
        assert policy is SelectiveTestingPolicy.disabled

    def test_blacklist(self):
        project = self.create_project()
        with mock.patch.object(project, 'get_config') as mock_get_config:
            with mock.patch.object(ProjectOptionsHelper, 'get_whitelisted_paths') as mock_get_whitelisted_paths:
                mock_get_config.return_value = {
                    'build.file-blacklist': ['a/a.txt'],
                    'bazel.selective-testing-enabled': True,
                }
                mock_get_whitelisted_paths.return_value = []
                policy, messages = get_selective_testing_policy(project, 'a' * 40, diff='diff')
        mock_get_config.assert_called_once_with('a' * 40, 'diff')
        mock_get_whitelisted_paths.assert_called_once_with(project)
        assert len(messages) > 0
        assert policy is SelectiveTestingPolicy.disabled

    def test_config(self):
        project = self.create_project()
        with mock.patch.object(project, 'get_config') as mock_get_config:
            with mock.patch.object(ProjectOptionsHelper, 'get_whitelisted_paths') as mock_get_whitelisted_paths:
                mock_get_config.return_value = {
                    'build.file-blacklist': [],
                    'bazel.selective-testing-enabled': False,
                }
                mock_get_whitelisted_paths.return_value = []
                policy, messages = get_selective_testing_policy(project, 'a' * 40, diff='diff')
        mock_get_config.assert_called_once_with('a' * 40, 'diff')
        mock_get_whitelisted_paths.assert_called_once_with(project)
        assert len(messages) > 0
        assert policy is SelectiveTestingPolicy.disabled
