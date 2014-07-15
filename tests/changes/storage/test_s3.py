from __future__ import absolute_import

import boto

from cStringIO import StringIO
from moto import mock_s3

from changes.storage.s3 import S3FileStorage
from changes.testutils import TestCase


class S3FileStorageTest(TestCase):
    @mock_s3
    def test_simple(self):
        fp = StringIO('hello world')

        conn = boto.connect_s3()
        conn.create_bucket('foo')

        storage = S3FileStorage(
            access_key='a' * 40,
            secret_key='b' * 40,
            bucket='foo',
            path='artifacts/',
        )
        storage.save('filename.txt', fp)

        result = storage.url_for('filename.txt')
        assert result.startswith('https://foo.s3.amazonaws.com/artifacts/filename.txt?')
