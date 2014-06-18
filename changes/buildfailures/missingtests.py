from __future__ import absolute_import

from jinja2 import Markup

from changes.buildfailures.base import BuildFailure


class MissingTests(BuildFailure):
    def get_html_label(self, build):
        return Markup('Tests were expected for all results, but some or all were missing.')
