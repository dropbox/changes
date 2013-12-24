from __future__ import absolute_import

from flask import current_app

from changes.backends.buildstep import BuildStep
from changes.config import db
from changes.models import RemoteEntity

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
        # TODO(dcramer): remove migration after 12/24
        if 'queued' not in build.data:
            entity = RemoteEntity.query.filter_by(
                provider='jenkins',
                internal_id=build.id,
                type='build',
            ).first()
            if entity is not None:
                build.data.update(entity.data)
                db.session.add(build)

        builder = self.get_builder()
        if not build.data:
            builder.create_build(build)
        else:
            builder.sync_build(build)
