from __future__ import absolute_import

from jinja2 import Markup

from changes.buildfailures.base import BuildFailure


class MalformedArtifact(BuildFailure):
    def get_html_label(self, build):
        return Markup('An artifact could not be parsed.')
