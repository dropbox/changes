from flask import session
from functools import wraps


def requires_auth(method):
    @wraps(method)
    def wrapped(*args, **kwargs):
        if not session.get('uid'):
            return '', 401
        return method(*args, **kwargs)
    return wrapped
