from __future__ import absolute_import

import os

from cStringIO import StringIO

from changes.storage.base import FileStorage

_cache = {}


class FileStorageCache(FileStorage):
    global _cache

    def __init__(self, **kwargs):
        super(FileStorageCache, self).__init__(**kwargs)

    def save(self, filename, fp, content_type=None, path=None):
        _cache[filename] = {
                    'content': fp.read(),
                    'content_type': content_type,
                    'path': path,
                }
        return filename

    def url_for(self, filename, expire=300):
        return 'url-not-implemented-for-filestoragecache'

    def get_size(self, filename):
        fp = StringIO(_cache[filename]['content'])
        fp.seek(0, os.SEEK_END)
        return fp.tell()

    def get_file(self, filename, offset=None, length=None):
        start_offset, end_offset = None, None
        if offset is not None:
            start_offset = offset
            if length is not None and length >= 1:
                end_offset = offset + length
        return StringIO(_cache[filename]['content'][start_offset:end_offset])

    @staticmethod
    def clear():
        _cache.clear()
