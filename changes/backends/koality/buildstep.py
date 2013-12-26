from __future__ import absolute_import

from flask import current_app

from changes.backends.buildstep import BuildStep
from changes.config import db
from changes.models import RemoteEntity

from .builder import KoalityBuilder


class KoalityBuildStep(BuildStep):
    def __init__(self, project_id=None):
        self.project_id = project_id

    def get_builder(self, app=current_app):
        return KoalityBuilder(app=app, project_id=self.project_id)

    def execute(self, job):
        # TODO(dcramer): remove migration after 12/24
        if not job.data:
            entity = RemoteEntity.query.filter_by(
                provider='koality',
                internal_id=job.id,
                type='build',
            ).first()
            if entity is not None:
                job.data = entity.data
                db.session.add(job)

        builder = self.get_builder()
        if not job.data:
            builder.create_job(job)
        else:
            builder.sync_job(job)

    def get_label(self):
        return 'Build project {0} on Koality'.format(self.project_id)
