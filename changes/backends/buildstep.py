from __future__ import absolute_import


class BuildStep(object):
    def execute(self, build):
        raise NotImplementedError
