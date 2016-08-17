from __future__ import absolute_import


class FileStorage(object):
    def __init__(self, path=''):
        self.path = path

    def save(self, filename, fp, content_type=None, path=None):
        raise NotImplementedError

    def url_for(self, filename, expire=300):
        raise NotImplementedError

    def get_file(self, filename, offset=None, length=None):
        raise NotImplementedError

    def get_size(self, filename):
        raise NotImplementedError
