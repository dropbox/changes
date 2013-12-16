from __future__ import absolute_import

from flask import current_app

from changes.backends.buildstep import BuildStep

from .builder import KoalityBuilder


class KoalityBuildStep(BuildStep):
    def get_builder(self, app=current_app):
        return KoalityBuilder(app=app)

    def execute(self, build):
        builder = self.get_builder()
        builder.create_build(build)

    def sync(self, build):
        builder = self.get_builder()
        builder.sync_build(build)
