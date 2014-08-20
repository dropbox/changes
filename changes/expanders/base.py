from __future__ import absolute_import


class Expander(object):
    def __init__(self, project, data):
        self.project = project
        self.data = data

    def validate(self):
        raise NotImplementedError

    def expand(self, max_executors):
        raise NotImplementedError
