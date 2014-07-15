from __future__ import absolute_import

from changes.storage.base import FileStorage


class DummyFileStorage(FileStorage):
    def save(self, filename, fp):
        pass

    def url_for(self, filename, expire=300):
        return ''
