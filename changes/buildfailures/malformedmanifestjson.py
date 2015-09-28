from __future__ import absolute_import

from jinja2 import Markup

from changes.buildfailures.base import BuildFailure


class MalformedManifestJson(BuildFailure):
    def get_html_label(self, build):
        return Markup('Infrastructure failure (manifest.json file was malformed or had incorrect JobStep id)')
