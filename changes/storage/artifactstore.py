from __future__ import absolute_import

import requests

from changes.lib.artifact_store_lib import ArtifactStoreClient
from flask import current_app

from changes.storage.base import FileStorage

ARTIFACTSTORE_PREFIX = 'artifactstore/'


class ArtifactStoreFileStorage(FileStorage):
    def __init__(self, base_url=None, path=''):
        self.base_url = base_url or current_app.config.get('ARTIFACTS_SERVER')
        self.path = path
        self.session = requests.Session()

    @staticmethod
    def get_filename_from_artifact_name(bucket_name, artifact_name):
        return 'buckets/%s/artifacts/%s' % (bucket_name, artifact_name)

    @staticmethod
    def get_artifact_name_from_filename(filename):
        url_parts = filename.split('/')
        if not (url_parts[0] == 'buckets' and url_parts[2] == 'artifacts'):
            raise ValueError('Invalid artifactstore url')
        bucket_name = url_parts[1]
        artifact_name = url_parts[3]
        return bucket_name, artifact_name

    def save(self, filename, fp, content_type=None, path=None):
        bucket_name, artifact_name = ArtifactStoreFileStorage.get_artifact_name_from_filename(filename)
        artifact_name = ArtifactStoreClient(self.base_url)\
            .write_streamed_artifact(bucket_name, artifact_name, fp.read(), path=path).name
        # Update the name to account for de-duplication
        return ArtifactStoreFileStorage.get_filename_from_artifact_name(bucket_name, artifact_name)

    def url_for(self, filename):
        return '{base_url}/{filename}/content'.format(
            base_url=self.base_url,
            filename=filename
        )

    def get_file(self, filename, offset=None, length=None):
        # TODO(paulruan): Have a reasonable file size limit
        bucket_name, artifact_name = ArtifactStoreFileStorage.get_artifact_name_from_filename(filename)
        return ArtifactStoreClient(self.base_url) \
            .get_artifact_content(bucket_name, artifact_name, offset, length)
