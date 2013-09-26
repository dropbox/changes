import logging

from sqlalchemy.orm import joinedload

from buildbox.backends.koality.backend import KoalityBackend
from buildbox.config import db
from buildbox.constants import Status
from buildbox.jobs.sync_build import sync_build
from buildbox.models import (
    Project, Build, RemoteEntity, EntityType
)


"""
- Poll for list of builds
- Poll any builds which are not marked as finished
- Timeout builds after 60 minutes which are marked as in progress
- Timeout builds after 120 minutes which are marked as queued
"""


class Poller(object):
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger('buildbox.poller')

    def get_backend(self):
        return KoalityBackend(
            app=self.app,
            base_url=self.app.config['KOALITY_URL'],
            api_key=self.app.config['KOALITY_API_KEY'],
        )

    def get_project_list(self):
        self.logger.info('Fetching project list')
        koality_projects = list(RemoteEntity.query.filter_by(
            type=EntityType.project, provider='koality'))
        if not koality_projects:
            return []
        project_list = list(Project.query.filter(Project.id.in_([
            re.internal_id for re in koality_projects
        ])).options(
            joinedload(Project.repository),
        ))

        return project_list

    def run(self):
        with self.app.app_context():
            self._run()

    def _run(self):
        project_list = self.get_project_list()

        # TODO(dcramer): we need to limit this to builds that have not been
        # finalized. Should we add RemoteEntity.finalized?
        pending_build_syncs = set()
        for project in project_list:
            self.logger.info('Fetching builds for project {%s}', project.slug)
            for build, created in self.get_backend().sync_build_list(project):
                if created:
                    self.logger.info('Spawning sync job for {%s}', build.id)
                    pending_build_syncs.add((project, build))

        db.session.commit()

        # self.logger.info('Finding in-progress builds to sync {%s}', project.slug)
        # unfinished = Build.query.join(
        #     RemoteEntity, Build.id == RemoteEntity.internal_id
        # ).filter(
        #     RemoteEntity.type == EntityType.build,
        #     RemoteEntity.provider == 'koality',
        #     Build.status != Status.finished,
        # ).options(
        #     joinedload(Build.project),
        #     joinedload(Build.project, Project.repository),
        # )
        # for build in unfinished:
        #     pending_build_syncs.add((build.project, build))

        for (project, build) in pending_build_syncs:
            # TODO: we should confirm that the build isnt queued.. or something
            sync_build.delay(
                build_id=build.id,
            )
