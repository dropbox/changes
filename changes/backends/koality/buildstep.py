from __future__ import absolute_import

from flask import current_app

from changes.backends.buildstep import BuildStep

from .builder import KoalityBuilder


class KoalityBuildStep(BuildStep):
    def __init__(self, project_id=None):
        self.project_id = project_id

    def get_builder(self, app=current_app):
        return KoalityBuilder(app=app, project_id=self.project_id)

    def get_label(self):
        return 'Build project {0} on Koality'.format(self.project_id)

    def execute(self, job):
        builder = self.get_builder()
        builder.create_job(job)

    def update(self, job):
        builder = self.get_builder()
        builder.sync_job(job)
