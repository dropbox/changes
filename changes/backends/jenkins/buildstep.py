from __future__ import absolute_import

from flask import current_app

from changes.backends.buildstep import BuildStep

from .builder import JenkinsBuilder


class JenkinsBuildStep(BuildStep):
    """
    Should execute be required to be idempotent (e.g. handle create + sync)
    or should we provide two APIs?
    """
    def get_builder(self, app=current_app):
        return JenkinsBuilder(app=app)

    def execute(self, build):
        builder = self.get_builder()
        builder.create_build(build)

    def sync(self, build):
        builder = self.get_builder()
        builder.sync_build(build)
