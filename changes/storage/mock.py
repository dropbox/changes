from __future__ import absolute_import

from cStringIO import StringIO

from changes.storage.base import FileStorage

_cache = {}


class FileStorageCache(FileStorage):
    global _cache

    def __init__(self, **kwargs):
        super(FileStorageCache, self).__init__(**kwargs)

    def save(self, filename, fp, content_type=None):
        _cache[filename] = {
                    'content': fp.read(),
                    'content_type': content_type,
                }

    def url_for(self, filename, expire=300):
        raise NotImplementedError

    def get_file(self, filename):
        return StringIO(_cache[filename]['content'])

    def get_content_type(self, filename):
        return _cache[filename]['content_type']

    @staticmethod
    def clear():
        _cache.clear()
