import logging

from buildbox.app import db
from buildbox.backends.koality.backend import KoalityBackend
from buildbox.config import settings
from buildbox.models import (
    Project, RemoteEntity, EntityType
)


"""
- Poll for list of builds
- Poll any builds which are not marked as finished
- Timeout builds after 60 minutes which are marked as in progress
- Timeout builds after 120 minutes which are marked as queued
"""


class Poller(object):
    def __init__(self):
        self.backend = KoalityBackend(
            settings['koality.url'],
            settings['koality.api_key'],
        )
        self.logger = logging.getLogger('buildbox.poller')

    def get_session(self):
        return db.get_session()

    def get_project_list(self):
        self.logger.info('Fetching project list')
        with self.get_session() as session:
            koality_projects = list(session.query(RemoteEntity).filter_by(
                type=EntityType.project, provider='koality'))
            if not koality_projects:
                return []
            project_list = session.query(Project).filter(Project.id.in_([
                re.internal_id for re in koality_projects
            ]))

        return project_list

    def run(self):
        project_list = self.get_project_list()
        for project in project_list:
            self.logger.info('Fetching builds for project {%s}', project.slug)
            build_list = self.backend.sync_build_list(project)
            for build in build_list:
                self.logger.info('Fetching details for build {%s}', build.id)
                self.sync_build_details(build)
