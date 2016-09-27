import logging
import uuid

from sqlalchemy.orm import joinedload, subqueryload_all

from changes.api.base import APIView, error
from changes.api.build_index import create_build, get_build_plans
from changes.constants import Cause, Result, Status
from changes.models.build import Build
from changes.models.phabricatordiff import PhabricatorDiff
from changes.models.project import (
    Project, ProjectConfigError, ProjectStatus, ProjectOptionsHelper)
from changes.utils.diff_parser import DiffParser
from changes.utils.project_trigger import files_changed_should_trigger_project
from changes.vcs.base import InvalidDiffError


class DiffBuildRetryAPIView(APIView):
    def post(self, diff_id):
        """
        Ask Changes to restart all builds for this diff. The response will be
        the list of all builds.
        """
        diff = self._get_diff_by_id(diff_id)
        if not diff:
            return error("Diff with ID %s does not exist." % (diff_id,))
        diff_parser = DiffParser(diff.source.patch.diff)
        files_changed = diff_parser.get_changed_files()
        try:
            projects = self._get_projects_for_diff(diff, files_changed)
        except InvalidDiffError:
            return error('Patch does not apply')
        except ProjectConfigError:
            return error('Project config is not in a valid format.')
        collection_id = uuid.uuid4()

        builds = self._get_builds_for_diff(diff)
        new_builds = []
        for project in projects:
            builds_for_project = [x for x in builds if x.project_id == project.id]
            if not builds_for_project:
                logging.warning('Project with id %s does not have a build.', project.id)
                continue
            build = max(builds_for_project, key=lambda x: x.number)
            if build.status is not Status.finished:
                continue
            if build.result is Result.passed:
                continue
            new_build = create_build(
                project=project,
                collection_id=collection_id,
                label=build.label,
                target=build.target,
                message=build.message,
                author=build.author,
                source=diff.source,
                cause=Cause.retry,
                selective_testing_policy=build.selective_testing_policy,
            )
            new_builds.append(new_build)
        return self.respond(new_builds)

    def _get_diff_by_id(self, diff_id):
        diffs = list(PhabricatorDiff.query.options(
            joinedload('source').joinedload('patch')
        ).filter(
            PhabricatorDiff.diff_id == diff_id
        ))
        if not diffs:
            return None
        assert len(diffs) == 1
        return diffs[0]

    def _get_projects_for_diff(self, diff, files_changed):
        projects = list(Project.query.options(
            subqueryload_all('plans'),
        ).filter(
            Project.status == ProjectStatus.active,
            Project.repository_id == diff.source.repository_id,
        ))
        project_options = ProjectOptionsHelper.get_options(projects, ['build.file-whitelist', 'phabricator.diff-trigger'])
        projects = [
            x for x in projects
            if get_build_plans(x) and
            project_options[x.id].get('phabricator.diff-trigger', '1') == '1' and
            files_changed_should_trigger_project(files_changed, x, project_options[x.id], diff.source.revision_sha, diff=diff.source.patch.diff)
        ]
        return projects

    def _get_builds_for_diff(self, diff):
        builds = list(Build.query.filter(
            Build.source_id == diff.source.id
        ))
        return builds
