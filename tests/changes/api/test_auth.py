import mock
import pytest

from uuid import uuid4

from changes.api.auth import (
    get_project_slug_from_project_id, get_project_slug_from_plan_id,
    get_project_slug_from_step_id,
    ResourceNotFound, requires_project_admin,
)
from changes.testutils import TestCase


class ProjectAdminHelpersTestCase(TestCase):

    def test_get_project_slug_from_project_id_success(self):
        project = self.create_project()
        assert project.slug == get_project_slug_from_project_id(1, 2, project_id=project.slug, other_args='test')

    def test_get_project_slug_from_project_id_not_found(self):
        with pytest.raises(ResourceNotFound):
            get_project_slug_from_project_id(project_id='does-not-exist')

    def test_get_project_slug_from_plan_id(self):
        project = self.create_project()
        plan = self.create_plan(project)
        assert project.slug == get_project_slug_from_plan_id(1, 2, plan_id=plan.id, other_args='test')

    def test_get_project_slug_from_plan_id_not_found(self):
        with pytest.raises(ResourceNotFound):
            get_project_slug_from_plan_id(plan_id=uuid4())

    def test_get_project_slug_from_step_id(self):
        project = self.create_project()
        plan = self.create_plan(project)
        step = self.create_step(plan)
        assert project.slug == get_project_slug_from_step_id(1, 2, step_id=step.id, other_args='test')

    def test_get_project_slug_from_step_id_not_found(self):
        with pytest.raises(ResourceNotFound):
            get_project_slug_from_step_id(step_id=uuid4())


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
