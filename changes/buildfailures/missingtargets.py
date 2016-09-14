from __future__ import absolute_import

from jinja2 import Markup

from changes.buildfailures.base import BuildFailure


class MissingTargets(BuildFailure):
    def get_html_label(self, build):
        return Markup('Some Bazel targets did not produce a test.xml artifact, most likely due to a build failure.')
