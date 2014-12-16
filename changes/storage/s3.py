from __future__ import absolute_import

import boto
import boto.s3.connection

from flask import current_app

from changes.utils.cache import memoize
from changes.storage.base import FileStorage


class S3FileStorage(FileStorage):
    def __init__(self, access_key=None, secret_key=None, bucket=None, path=''):
        config = current_app.config

        self.access_key = access_key or config.get('S3_ACCESS_KEY')
        self.secret_key = secret_key or config.get('S3_SECRET_KEY')
        self.bucket_name = bucket or config.get('S3_BUCKET')
        self.path = path

    @memoize
    def connection(self):
        return self.get_connection()

    @memoize
    def bucket(self):
        return self.get_bucket(self.connection)

    def get_connection(self):
        return boto.connect_s3(
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
        )

    def get_bucket(self, connection):
        return connection.get_bucket(self.bucket_name)

    def get_file_path(self, filename):
        return '/'.join([self.path.rstrip('/'), filename])

    def save(self, filename, fp, content_type=None):
        key = self.bucket.new_key(self.get_file_path(filename))
        if content_type:
            key.content_type = content_type
        key.set_contents_from_file(fp)
        key.set_acl('private')

    def url_for(self, filename, expire=300):
        key = self.bucket.get_key(self.get_file_path(filename))
        return key.generate_url(300)

    def get_file(self, filename):
        return self.bucket.get_key(self.get_file_path(filename))

    def get_content_type(self, filename):
        return self.bucket.get_key(self.get_file_path(filename)).content_type
