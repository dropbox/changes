from __future__ import absolute_import

from cStringIO import StringIO

from changes.storage.base import FileStorage


class DummyFileStorage(FileStorage):
    def save(self, filename, fp):
        pass

    def url_for(self, filename, expire=300):
        return ''

    def get_file(self, filename):
        return StringIO()
