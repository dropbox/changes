from __future__ import absolute_import

import requests

from cStringIO import StringIO
from flask import current_app

from changes.storage.base import FileStorage

ARTIFACTSTORE_PREFIX = 'artifactstore/'


class ArtifactStoreFileStorage(FileStorage):
    def __init__(self, base_url=None, path=''):
        self.base_url = base_url or current_app.config.get('ARTIFACTS_SERVER')
        self.path = path
        self.session = requests.Session()

    def save(self, filename, fp, content_type=None):
        # We don't support this yet, do this directly through artifact_store_lib.py
        raise NotImplementedError

    def url_for(self, filename):
        return '{base_url}/{filename}/content'.format(
            base_url=self.base_url,
            filename=filename
        )

    def get_file(self, filename, offset=None, length=None):
        # TODO(paulruan): Have a reasonable file size limit
        headers = {}
        if offset is not None:
            if length is not None and length >= 1:
                headers['Range'] = 'bytes=%d-%d' % (offset, offset + length - 1)
            else:
                headers['Range'] = 'bytes=%d-' % (offset)
        resp = self.session.get(self.url_for(filename), timeout=15, headers=headers)
        resp.raise_for_status()
        return StringIO(resp.content)

    def get_content_type(self, filename):
        # TODO: We should be able to detect filetype from name
        return 'application/octet-stream'
