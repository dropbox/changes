from __future__ import absolute_import

from cStringIO import StringIO

from changes.storage.base import FileStorage

_cache = {}


class FileStorageCache(FileStorage):
    global _cache

    def __init__(self, **kwargs):
        super(FileStorageCache, self).__init__(**kwargs)

    def save(self, filename, fp):
        _cache[filename] = fp.read()

    def url_for(self, filename, expire=300):
        raise NotImplementedError

    def get_file(self, filename):
        return StringIO(_cache[filename])

    @staticmethod
    def clear():
        _cache.clear()
