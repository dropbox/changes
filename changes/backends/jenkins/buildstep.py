from __future__ import absolute_import

from flask import current_app

from changes.backends.buildstep import BuildStep

from .builder import JenkinsBuilder


class JenkinsBuildStep(BuildStep):
    """
    Should execute be required to be idempotent (e.g. handle create + sync)
    or should we provide two APIs?
    """
    def __init__(self, job_name=None):
        self.job_name = job_name

    def get_builder(self, app=current_app):
        return JenkinsBuilder(app=app, job_name=self.job_name)

    def execute(self, build):
        builder = self.get_builder()
        builder.create_build(build)

    def sync(self, build):
        builder = self.get_builder()
        builder.sync_build(build)
