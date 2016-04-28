from __future__ import absolute_import

import logging

from flask import current_app
from changes.api.build_index import BuildIndexAPIView
from changes.models.project import (
    Project, ProjectStatus, ProjectConfigError, ProjectOptionsHelper)
from changes.models.revision import Revision
from changes.utils.project_trigger import files_changed_should_trigger_project
from changes.vcs.base import ConcurrentUpdateError, UnknownRevision


def revision_created_handler(revision_sha, repository_id, **kwargs):
    revision = Revision.query.filter(
        Revision.sha == revision_sha,
        Revision.repository_id == repository_id,
    ).first()
    if not revision:
        return

    handler = CommitTrigger(revision)
    handler.run()


class CommitTrigger(object):
    logger = logging.getLogger('build_revision')

    def __init__(self, revision):
        self.repository = revision.repository
        self.revision = revision

    def get_project_list(self):
        return list(Project.query.filter(
            Project.repository_id == self.revision.repository_id,
            Project.status == ProjectStatus.active,
        ))

    def get_changed_files(self):
        vcs = self.repository.get_vcs()
        if not vcs:
            raise NotImplementedError
        # Make sure the repo exists on disk.
        if not vcs.exists():
            vcs.clone()

        try:
            return vcs.get_changed_files(self.revision.sha)
        except UnknownRevision:
            # Maybe the repo is stale; update.
            try:
                vcs.update()
            except ConcurrentUpdateError:
                # Retry once if it was already updating.
                vcs.update()
            # If it doesn't work this time, we have
            # a problem. Let the exception escape.
            return vcs.get_changed_files(self.revision.sha)

    def run(self):
        revision = self.revision

        project_list = self.get_project_list()
        if not project_list:
            return

        options = ProjectOptionsHelper.get_options(project_list, [
            'build.branch-names',
            'build.commit-trigger',
            'build.file-whitelist',
        ])

        files_changed = self.get_changed_files()

        projects_to_build = []
        for project in project_list:
            if options[project.id].get('build.commit-trigger', '1') != '1':
                self.logger.info('build.commit-trigger is disabled for project %s', project.slug)
                continue

            branch_names = filter(bool, options[project.id].get('build.branch-names', '*').split(' '))
            if not revision.should_build_branch(branch_names):
                self.logger.info('No branches matched build.branch-names for project %s', project.slug)
                continue

            try:
                if not files_changed_should_trigger_project(files_changed, project, options[project.id], revision.sha):
                    self.logger.info('No changed files matched project trigger for project %s', project.slug)
                    continue
            except ProjectConfigError:
                author_name = '(unknown)'
                if revision.author_id:
                    author_name = revision.author.name
                self.logger.error('Project config for project %s is not in a valid format. Author is %s.', project.slug, author_name, exc_info=True)

            projects_to_build.append(project.slug)

        for project_slug in projects_to_build:
            data = {
                'sha': revision.sha,
                'project': project_slug,
                'tag': 'commit',
            }
            with current_app.test_request_context('/api/0/builds/', method='POST', data=data):
                try:
                    response = BuildIndexAPIView().post()
                except Exception as e:
                    self.logger.exception('Failed to create build: %s' % (e,))
                else:
                    if isinstance(response, (list, tuple)):
                        response, status = response
                        if status != 200:
                            self.logger.error('Failed to create build: %s' % (response,), extra={
                                'data': data,
                            })
