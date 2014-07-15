from __future__ import absolute_import


class FileStorage(object):
    def __init__(self, path=''):
        self.path = path

    def save(self, filename, fp):
        raise NotImplementedError

    def url_for(self, filename, expire=300):
        raise NotImplementedError
