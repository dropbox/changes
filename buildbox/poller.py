import logging

from collections import defaultdict
from Queue import Queue, Empty
from sqlalchemy.orm import joinedload
from threading import Thread

from buildbox.app import db
from buildbox.backends.koality.backend import KoalityBackend
from buildbox.config import settings
from buildbox.constants import Status
from buildbox.models import (
    Project, Build, RemoteEntity, EntityType
)


"""
- Poll for list of builds
- Poll any builds which are not marked as finished
- Timeout builds after 60 minutes which are marked as in progress
- Timeout builds after 120 minutes which are marked as queued
"""


class Worker(Thread):
    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue
        self.results = defaultdict(list)

    def run(self):
        while True:
            try:
                ident, func, args, kwargs = self.queue.get_nowait()
            except Empty:
                break

            try:
                result = func(*args, **kwargs)
                self.results[ident].append(result)
            except Exception, e:
                self.results[ident].append(e)
            finally:
                self.queue.task_done()

        return self.results


class ThreadPool(object):
    def __init__(self, workers=10):
        self.queue = Queue()
        self.workers = []
        for worker in xrange(workers):
            self.workers.append(Worker(self.queue))

    def add(self, ident, func, args=None, kwargs=None):
        if args is None:
            args = ()
        if kwargs is None:
            kwargs = {}
        task = (ident, func, args, kwargs)
        self.queue.put_nowait(task)

    def join(self):
        for worker in self.workers:
            worker.start()

        results = defaultdict(list)
        for worker in self.workers:
            worker.join()
            for k, v in worker.results.iteritems():
                results[k].extend(v)
        return results


class Poller(object):
    def __init__(self):
        self.logger = logging.getLogger('buildbox.poller')

    def get_session(self):
        return db.get_session()

    def get_backend(self):
        return KoalityBackend(
            settings['koality.url'],
            settings['koality.api_key'],
        )

    def get_project_list(self):
        self.logger.info('Fetching project list')
        with self.get_session() as session:
            koality_projects = list(session.query(RemoteEntity).filter_by(
                type=EntityType.project, provider='koality'))
            if not koality_projects:
                return []
            project_list = list(session.query(Project).filter(Project.id.in_([
                re.internal_id for re in koality_projects
            ])).options(
                joinedload(Project.repository),
            ))

        return project_list

    def run(self):
        project_list = self.get_project_list()

        pool = ThreadPool()
        for project in project_list:
            self.logger.info('Fetching builds for project {%s}', project.slug)
            pool.add(
                ident=project,
                func=self.get_backend().sync_build_list,
                args=[project],
            )

        # TODO(dcramer): we need to limit this to builds that have not been
        # finalized. Should we add RemoteEntity.finalized?
        pending_build_syncs = set()
        for project, build_list in pool.join().iteritems():
            for build in build_list[0]:
                pending_build_syncs.add((project, build))

        self.logger.info('Finding in-progress builds to sync {%s}', project.slug)
        with self.get_session() as session:
            unfinished = session.query(Build).join(
                RemoteEntity, Build.id == RemoteEntity.internal_id
            ).filter(
                RemoteEntity.type == EntityType.build,
                RemoteEntity.provider == 'koality',
                Build.status != Status.finished,
            ).options(
                joinedload(Build.project),
                joinedload(Build.project, Project.repository),
            )
            for build in unfinished:
                pending_build_syncs.add((build.project, build))

        pool = ThreadPool()
        for (project, build) in pending_build_syncs:
            pool.add(
                ident=build.id,
                func=self.get_backend().sync_build_details,
                kwargs={
                    'build': build,
                    'project': project,
                },
            )

        self.logger.info('Syncing %d builds', len(pending_build_syncs))
        pool.join()
