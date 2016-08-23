from __future__ import absolute_import, print_function

from flask import current_app, session, request
from fnmatch import fnmatch
from functools import wraps
from typing import Optional  # NOQA

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
                return self.respond({
                    'error': 'Not logged in.'
                }, status_code=401)
            if user.is_admin:
                # global admins are automatically project admins
                return method(self, *args, **kwargs)
            if user.project_permissions is not None:
                try:
                    slug = get_project_slug(self, *args, **kwargs)
                except ResourceNotFound as e:
                    return self.respond({
                        'error': '{}'.format(e)
                    }, status_code=404)
                for p in user.project_permissions:
                    if fnmatch(slug, p):
                        return method(self, *args, **kwargs)
            return self.respond({
                'error': 'User does not have access to this project.'
            }, status_code=403)
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
