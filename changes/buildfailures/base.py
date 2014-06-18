from __future__ import absolute_import


class BuildFailure(object):
    def get_html_label(self, build):
        raise NotImplementedError
