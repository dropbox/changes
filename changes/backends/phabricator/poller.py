#!/usr/bin/env
"""
Phabricator Poller
"""
from datetime import datetime
from phabricator import Phabricator

from changes.config import db
from changes.models import (
    RemoteEntity, Project, EntityType, Change, Build
)


class PhabricatorPoller(object):
    provider = 'phabricator'

    def __init__(self, client, *args, **kwargs):
        # The default client uses ~/.arcrc
        self.client = client or Phabricator()
        super(PhabricatorPoller, self).__init__(*args, **kwargs)

    def _populate_project_cache(self):
        entity_map = dict(
            (e.internal_id, e.remote_id)
            for e in RemoteEntity.query.filter_by(
                provider='phabricator',
                type=EntityType.project,
            )
        )
        project_list = Project.query.filter(
            Project.id.in_(entity_map.keys()))
        self._arcproject_to_project_id = {}
        self._project_id_to_arcproject = {}
        self._project_cache = {}
        for project in project_list:
            self._arcproject_to_project_id[entity_map[project.id]] = project.id
            self._project_id_to_arcproject[project.id] = entity_map[project.id]
            self._project_cache[project.id] = project

    def _get_project_from_arcproject(self, name):
        if name not in self._arcproject_to_project:
            entity = RemoteEntity.query.filter_by(
                provider=self.provider,
                type=EntityType.project,
                remote_id=name,
            )[0]

            project = Project.query.get(entity.internal_id)
            self._arcproject_to_project[name] = project
            self._project_to_arcproject[project] = name
        return self._arcproject_to_project[name]

    def _yield_revisions(self):
        # the API response does not include the arcanist project, so we
        # must query each individually
        for project in self._project_cache.itervalues():
            arcproject = self._project_id_to_arcproject[project.id]
            results = self.client.differential.query(
                arcanistProjects=[arcproject],
                limit=100,
            )
            for result in results:
                yield (project, result)

    def _get_label_from_revision(self, revision):
        return 'D{0}: {1}'.format(revision['id'], revision['title'])[:128]

    def _get_change_from_revision(self, project, revision):
        try:
            entity = RemoteEntity.query.filter_by(
                provider=self.provider,
                type=EntityType.change,
                remote_id=revision['id'],
            )[0]
        except IndexError:
            return

        return Change.query.get(entity.internal_id)

    def _create_change_from_revision(self, project, revision):
        change = Change(
            repository=project.repository,
            project=project,
            date_created=datetime.utcfromtimestamp(float(revision['dateCreated'])),
            date_modified=datetime.utcfromtimestamp(float(revision['dateModified'])),
        )
        db.session.add(change)

        entity = RemoteEntity(
            type=EntityType.change,
            internal_id=change.id,
            remote_id=revision['id'],
            provider=self.provider,
        )
        db.session.add(entity)

        return change

    def sync_revision_list(self):
        """
        Fetch a list of all diffs, and create any changes that are
        missing (via the API).
        """
        self._populate_project_cache()
        for project, revision in self._yield_revisions():
            self.sync_revision(project, revision)

    def sync_revision(self, project, revision):
        change = self._get_change_from_revision(project, revision)
        if not change:
            change = self._create_change_from_revision(project, revision)

        message = self.client.differential.getcommitmessage(
            revision_id=revision['id']).response
        label = self._get_label_from_revision(revision)
        if change.label != label:
            change.label = label
        if change.message != message:
            change.message = message

        db.session.add(change)

        self.sync_diff_list(change, revision['id'])

        return change

    def _yield_diffs(self, revision_id):
        # the API response does not include the arcanist project, so we
        # must query each individually
        results = self.client.differential.querydiffs(
            revisionIDs=[revision_id],
        )

        for key in sorted(results.keys()):
            yield results[key]

    def _get_build_from_diff(self, change, diff):
        try:
            entity = RemoteEntity.query.filter_by(
                provider=self.provider,
                type=EntityType.build,
                remote_id=diff['id'],
            )[0]
        except IndexError:
            return

        return Build.query.get(entity.internal_id)

    def _create_build_from_diff(self, change, diff):
        build = Build(
            change=change,
            repository=change.repository,
            project=change.project,
            parent_revision_sha=diff['sourceControlBaseRevision'],
            label='Diff ID {0}: {1}'.format(
                diff['id'], diff['description'] or 'Initial')[:128],
        )
        db.session.add(build)

        entity = RemoteEntity(
            type=EntityType.build,
            internal_id=build.id,
            remote_id=diff['id'],
            provider=self.provider,
        )
        db.session.add(entity)

        return build

    def sync_diff_list(self, change, revision_id):
        for diff in self._yield_diffs(revision_id):
            self.sync_diff(change, diff)

    def sync_diff(self, change, diff):
        build = self._get_build_from_diff(change, diff)
        if not build:
            build = self._create_build_from_diff(change, diff)
        db.session.add(build)

        return build
