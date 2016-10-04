from __future__ import absolute_import, print_function

from flask import current_app, session, request
from fnmatch import fnmatch
from functools import wraps
from typing import Optional  # NOQA

from changes.api.base import error
from changes.models.plan import Plan
from changes.models.project import Project
from changes.models.step import Step
from changes.models.user import User


NOT_SET = object()


def requires_auth(method):
    """
    Require an authenticated user on given method.

    Return a 401 Unauthorized status on failure.

    >>> @requires_admin
    >>> def post(self):
    >>>     # ...
    """
    @wraps(method)
    def wrapped(*args, **kwargs):
        user = get_current_user()
        if user is None:
            return '', 401
        return method(*args, **kwargs)
    return wrapped


def requires_admin(method):
    """
    Require an authenticated user with admin privileges.

    Return a 401 Unauthorized if the user is not authenticated, or a
    403 Forbidden if the user is lacking permissions.

    >>> @requires_admin
    >>> def post(self):
    >>>     # ...
    """
    @wraps(method)
    def wrapped(*args, **kwargs):
        user = get_current_user()
        if user is None:
            return '', 401
        if not user.is_admin:
            return '', 403
        return method(*args, **kwargs)
    return wrapped


class ResourceNotFound(Exception):
    pass


def get_project_slug_from_project_id(*args, **kwargs):
    """
    Get the project slug from the project ID. This function assumes that
    the project ID is passed as the keyword argument `project_id`.

    Returns:
        basestring - project slug
    Raises:
        ResourceNotFound - if the project is not found
    """
    project_id = kwargs['project_id']
    # use our custom .get() function instead of .query.get()
    project = Project.get(project_id)
    if project is None:
        raise ResourceNotFound('Project with ID {} not found.'.format(project_id))
    return project.slug


def get_project_slug_from_plan_id(*args, **kwargs):
    """
    Get the project slug from the plan ID. This function assumes that
    the plan ID is passed as the keyword argument `plan_id`.

    Returns:
        basestring - project slug
    Raises:
        ResourceNotFound - if the plan is not found
    """
    plan_id = kwargs['plan_id']
    plan = Plan.query.get(plan_id)
    if plan is None:
        raise ResourceNotFound('Plan with ID {} not found.'.format(plan_id))
    return plan.project.slug


def get_project_slug_from_step_id(*args, **kwargs):
    """
    Get the project slug from the step ID. This function assumes that
    the step ID is passed as the keyword argument `step_id`.

    Returns:
        basestring - project slug
    Raises:
        ResourceNotFound - if the step is not found
    """
    step_id = kwargs['step_id']
    step = Step.query.get(step_id)
    if step is None:
        raise ResourceNotFound('Step with ID {} not found.'.format(step_id))
    return step.plan.project.slug


def user_has_project_permission(user, project_slug):
    # type: (User, str) -> bool
    """
    Given a user and a project slug, determine if the user has admin permission
    for this project.
    """
    if user.is_admin:
        return True
    if user.project_permissions is not None:
        for p in user.project_permissions:
            if fnmatch(project_slug, p):
                return True
    return False


def requires_project_admin(get_project_slug):
    """
    Require an authenticated user with project admin privileges.

    Return a 401 Unauthorized if the user is not authenticated, or a
    403 Forbidden if the user is lacking permissions.

    Args:
        get_project_slug: This is a function that will be given the exact
            same argument as the wrapped function. This function should
            return the project slug (not ID!). Raise `ResourceNotFound`
            if the associated resource (plan, step, project, etc.) cannot
            be found.
    """
    def decorator(method):
        @wraps(method)
        def wrapped(self, *args, **kwargs):
            user = get_current_user()
            if user is None:
                return error('Not logged in', http_code=401)
            try:
                slug = get_project_slug(self, *args, **kwargs)
            except ResourceNotFound as e:
                return error('{}'.format(e), http_code=404)
            if user_has_project_permission(user, slug):
                return method(self, *args, **kwargs)
            return error('User does not have access to this project.', http_code=403)
        return wrapped
    return decorator


def get_current_user():
    # type: () -> Optional[User]
    """
    Return the currently authenticated user.

    Determines authenticated user based on session (default) or headers from an
    authenticating proxy (only if PP_AUTH is enabled in the config).
    """
    if getattr(request, 'current_user', NOT_SET) is NOT_SET:
        if current_app.config.get('PP_AUTH', False):
            email = request.headers.get('X-PP-USER')
            if email is None:
                request.gcurrent_user = None
            else:
                request.gcurrent_user = User.query.filter_by(email=email).first()
        else:
            if session.get('uid') is None:
                request.gcurrent_user = None
            else:
                request.gcurrent_user = User.query.get(session['uid'])
                if request.gcurrent_user is None:
                    del session['uid']
    return request.gcurrent_user
