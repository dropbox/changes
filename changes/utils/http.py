from __future__ import absolute_import, print_function

from flask import current_app


def build_web_uri(path, app=current_app):
    return str('{base_uri}/{path}'.format(
        base_uri=app.config['WEB_BASE_URI'].rstrip('/'),
        path=path.lstrip('/'),
    ))


def build_internal_uri(path, app=current_app):
    return str('{base_uri}/{path}'.format(
        base_uri=app.config['INTERNAL_BASE_URI'].rstrip('/'),
        path=path.lstrip('/'),
    ))
