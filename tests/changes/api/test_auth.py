import mock
import pytest

from changes.api.auth import (
    ResourceNotFound, requires_project_admin,
)
from changes.testutils import TestCase


class ProjectAdminTestCase(TestCase):

    _project_slug = 'other:project-a'

    class DidExecute(Exception):
        pass

    def _get_project_slug(self):
        return self._project_slug

    def _get_project_slug_error(self):
        raise ResourceNotFound

    @requires_project_admin(_get_project_slug)
    def _sample_function(self):
        raise self.DidExecute

    @requires_project_admin(_get_project_slug_error)
    def _sample_function_error(self):
        raise self.DidExecute

    respond = mock.MagicMock()

    def test_global_admin(self):
        user = self.create_user(email='user1@example.com', is_admin=True)
        with mock.patch('changes.api.auth.get_current_user') as mocked:
            mocked.return_value = user
            with pytest.raises(self.DidExecute):
                self._sample_function()

    def test_authenticated_exact(self):
        user = self.create_user(email='user1@example.com', project_permissions=['someproject', 'other:project-a', 'otherproject'])
        with mock.patch('changes.api.auth.get_current_user') as mocked:
            mocked.return_value = user
            with pytest.raises(self.DidExecute):
                self._sample_function()

    def test_authenticated_pattern_trailing(self):
        user = self.create_user(email='user1@example.com', project_permissions=['someproject', 'other:*', 'otherproject'])
        with mock.patch('changes.api.auth.get_current_user') as mocked:
            mocked.return_value = user
            with pytest.raises(self.DidExecute):
                self._sample_function()

    def test_authenticated_pattern_both(self):
        user = self.create_user(email='user1@example.com', project_permissions=['someproject', '*other:*', 'otherproject'])
        with mock.patch('changes.api.auth.get_current_user') as mocked:
            mocked.return_value = user
            with pytest.raises(self.DidExecute):
                self._sample_function()

    def test_not_authenticated_none(self):
        user = self.create_user(email='user1@example.com')
        with mock.patch('changes.api.auth.get_current_user') as mocked:
            mocked.return_value = user
            self._sample_function()
            _, kwargs = self.respond.call_args
            assert kwargs['status_code'] == 403

    def test_not_authenticated_pattern(self):
        user = self.create_user(email='user1@example.com', project_permissions=['someproject*', 'otherproject'])
        with mock.patch('changes.api.auth.get_current_user') as mocked:
            mocked.return_value = user
            self._sample_function()
            _, kwargs = self.respond.call_args
            assert kwargs['status_code'] == 403

    def test_no_user(self):
        with mock.patch('changes.api.auth.get_current_user') as mocked:
            mocked.return_value = None
            self._sample_function()
            _, kwargs = self.respond.call_args
            assert kwargs['status_code'] == 401

    def test_resource_not_found(self):
        user = self.create_user(email='user1@example.com', project_permissions=['someproject', 'other:project-a', 'otherproject'])
        with mock.patch('changes.api.auth.get_current_user') as mocked:
            mocked.return_value = user
            status = self._sample_function_error()
            _, kwargs = self.respond.call_args
            assert kwargs['status_code'] == 404
