from __future__ import absolute_import, print_function

import logging

from collections import defaultdict
from flask import current_app
from fnmatch import fnmatch

from changes.api.build_index import BuildIndexAPIView
from changes.config import db
from changes.models import ProjectOption, ProjectStatus, Project, Revision
from changes.utils.diff_parser import DiffParser


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

    def get_options(self, project_list):
        options_query = db.session.query(
            ProjectOption.project_id, ProjectOption.name, ProjectOption.value
        ).filter(
            ProjectOption.project_id.in_(p.id for p in project_list),
            ProjectOption.name.in_([
                'build.branch-names',
                'build.commit-trigger',
                'build.file-whitelist',
            ])
        )

        options = defaultdict(dict)
        for project_id, option_name, option_value in options_query:
            options[project_id][option_name] = option_value

        return options

    def should_build_branch(self, allowed_branches):
        if not self.revision.branches and '*' in allowed_branches:
            return True

        for branch in self.revision.branches:
            if any(fnmatch(branch, pattern) for pattern in allowed_branches):
                return True
        return False

    def get_changed_files(self):
        vcs = self.repository.get_vcs()
        if not vcs:
            raise NotImplementedError

        diff = vcs.export(self.revision.sha)
        diff_parser = DiffParser(diff)
        parsed_diff = diff_parser.parse()

        results = set()
        for info in parsed_diff:
            if info['new_filename']:
                results.add(info['new_filename'][2:])
            if info['old_filename']:
                results.add(info['old_filename'][2:])
        return results

    def in_file_whitelist(self, files_changed, file_whitelist):
        for filename in files_changed:
            if any(fnmatch(filename, pattern) for pattern in file_whitelist):
                return True
        return False

    def run(self):
        revision = self.revision

        project_list = self.get_project_list()
        if not project_list:
            return

        options = self.get_options(project_list)

        if any(o.get('build.file-whitelist') for o in options.values()):
            files_changed = self.get_changed_files()
        else:
            files_changed = None

        projects_to_build = []
        for project in project_list:
            if options[project.id].get('build.commit-trigger', '1') != '1':
                self.logger.info('build.commit-trigger is disabled for project %s', project.slug)
                continue

            branch_names = filter(bool, options[project.id].get('build.branch-names', '*').split(' '))
            if not self.should_build_branch(branch_names):
                self.logger.info('No branches matched build.branch-names for project %s', project.slug)
                continue

            file_whitelist = filter(bool, options[project.id].get('build.file-whitelist', '').splitlines())
            if file_whitelist and not self.in_file_whitelist(files_changed, file_whitelist):
                self.logger.info('No changed files matched build.file-whitelist for project %s', project.slug)
                continue

            projects_to_build.append(project.slug)

        for project_slug in projects_to_build:
            data = {
                'sha': revision.sha,
                'project': project_slug,
            }
            with current_app.test_request_context('/api/0/builds/', method='POST', data=data):
                try:
                    response = BuildIndexAPIView().post()
                except Exception as e:
                    print(e)
                    self.logger.exception('Failed to create build: %s' % (e,))
                else:
                    print(response)
                    if isinstance(response, (list, tuple)):
                        response, status = response
                        if status != 200:
                            self.logger.error('Failed to create build: %s' % (response,), extra={
                                'data': data,
                            })
