from __future__ import absolute_import, division, print_function

import os.path


class Vcs(object):
    def __init__(self, path, url):
        self.path = path
        self.url = url

        self._path_exists = None

    def run(self, *args, **kwargs):
        from subprocess import check_output

        if self.exists():
            kwargs.setdefault('cwd', self.path)

        return check_output(*args, **kwargs)

    def exists(self):
        return os.path.exists(self.path)

    def clone(self):
        raise NotImplementedError

    def update(self):
        raise NotImplementedError

    def get_revision(self, id):
        """
        Return a ``Revision`` given by ``id`.
        """
        raise NotImplementedError


class Revision(object):
    def __init__(self, id, message, author):
        self.id = id
        self.message = message
        self.author = author

    @property
    def subject(self):
        return self.message.splitlines()[0]
