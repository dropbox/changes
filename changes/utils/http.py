from __future__ import absolute_import, print_function

from flask import current_app
from typing import Any  # NOQA
import uuid  # NOQA


def build_web_uri(path, app=current_app):
    return _concat_uri_path(app.config['WEB_BASE_URI'], path)


def build_internal_uri(path, app=current_app):
    return _concat_uri_path(app.config['INTERNAL_BASE_URI'], path)


def build_patch_uri(patch_id, app=current_app):
    """
    Generate the URI to be used by slaves for fetching a patch.

    Args:
        patch_id (uuid.UUID): Patch ID.
        app: Current application.

    Returns:
        str: URI to be used when fetching the patch on a build slave.

    """
    # type: (uuid.UUID, Any) -> str
    base = app.config.get('PATCH_BASE_URI') or app.config['INTERNAL_BASE_URI']
    return _concat_uri_path(base,
                            '/api/0/patches/{0}/?raw=1'.format(patch_id.hex))


def _concat_uri_path(base_uri, path):
    # type: (str, str) -> str
    return str('{base_uri}/{path}'.format(base_uri=base_uri.rstrip('/'),
                                          path=path.lstrip('/'), ))
