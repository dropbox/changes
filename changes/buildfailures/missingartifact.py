from __future__ import absolute_import

from jinja2 import Markup

from changes.buildfailures.base import BuildFailure


class MissingArtifact(BuildFailure):
    def get_html_label(self, build):
        # TODO(dcramer): we need arbitrary data with build failures so this can
        # say *what* artifact
        return Markup('A critical artifact was expected, but was not collected.')
