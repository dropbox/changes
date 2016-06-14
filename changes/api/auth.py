from __future__ import absolute_import, print_function

from flask import current_app, session, request
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
