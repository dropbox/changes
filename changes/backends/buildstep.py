from __future__ import absolute_import


class BuildStep(object):
    def execute(self, job):
        raise NotImplementedError

    def get_label(self):
        raise NotImplementedError
