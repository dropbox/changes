from __future__ import absolute_import

from changes.storage.base import FileStorage

from flask import current_app


class ArtifactStoreFileStorage(FileStorage):
    def __init__(self, base_url=None, path=''):
        self.base_url = base_url or current_app.config.get('ARTIFACTS_SERVER')
        self.path = path

    def save(self, filename, fp, content_type=None):
        # We don't actually write file contents anywhere
        pass

    def url_for(self, filename):
        return '{base_url}/{filename}/content'.format(
            base_url=self.base_url,
            filename=filename
        )

    def get_file(self, filename):
        # TODO: Make a request and get data
        raise NotImplementedError

    def get_content_type(self, filename):
        # TODO: We should be able to detect filetype from name
        return 'application/octet-stream'
