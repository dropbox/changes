from __future__ import absolute_import

from jinja2 import Markup

from changes.buildfailures.base import BuildFailure


class MissingManifestJson(BuildFailure):
    def get_html_label(self, build):
        return Markup('Infrastructure failure (missing manifest file)')
