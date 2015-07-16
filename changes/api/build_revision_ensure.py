from __future__ import absolute_import, division, unicode_literals

import logging
import uuid

from flask.ext.restful import reqparse
from changes.constants import ProjectStatus
from changes.api.base import APIView, error
from changes.api.build_index import (
    identify_revision, get_repository_by_callsign, get_repository_by_url, try_get_projects_and_repository, MissingRevision, get_build_plans, create_build
)
from changes.models import (
    Project, ProjectOptionsHelper, Build, Source,
)
from changes.utils.diff_parser import DiffParser
from changes.utils.whitelist import in_project_files_whitelist
from changes.vcs.base import UnknownRevision


class BuildRevisionEnsureAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('sha', type=str, required=True)
    parser.add_argument('project', type=lambda x: Project.query.filter(
        Project.slug == x,
        Project.status == ProjectStatus.active,
    ).first())
    parser.add_argument('repository', type=get_repository_by_url)
    parser.add_argument(
        'repository[phabricator.callsign]', type=get_repository_by_callsign)

    def _get_changed_files(self, repository, revision):
        vcs = repository.get_vcs()
        if not vcs:
            raise NotImplementedError
        # Make sure the repo exists on disk.
        if not vcs.exists():
            vcs.clone()

        diff = None
        try:
            diff = vcs.export(revision.sha)
        except UnknownRevision:
            # Maybe the repo is stale; update.
            vcs.update()
            # If it doesn't work this time, we have
            # a problem. Let the exception escape.
            diff = vcs.export(revision.sha)

        diff_parser = DiffParser(diff)
        return diff_parser.get_changed_files()

    def post(self):
        """This API ensures that given a valid sha, there is a corresponding set
        of builds for it.

        It returns exactly one build per project, after applying whitelist. If no
        build has been created for a project, it is created. If multiple builds
        have been created for a project, it returns the latest one.

        The returned builds do NOT necessarily have the same collection ID.

        The required arguments are the commit hash and one of the three:
        project (slug), repository (url), or the phabricator callsign.
        """
        args = self.parser.parse_args()

        if not (args.project or args.repository or args['repository[phabricator.callsign]']):
            return error("Project or repository must be specified",
                         problems=["project", "repository",
                                   "repository[phabricator.callsign]"])

        projects, repository = try_get_projects_and_repository(args)

        if not projects:
            return error("Unable to find project(s).")

        try:
            revision = identify_revision(repository, args.sha)
        except MissingRevision:
            # if the default fails, we absolutely can't continue and the
            # client should send a valid revision
            return error("Unable to find commit %s in %s." % (
                args.sha, repository.url), problems=['sha', 'repository'])

        if revision:
            author = revision.author
            label = revision.subject
            message = revision.message
            sha = revision.sha
        else:
            return error("Unable to find revision for commit %s in %s." % (
                args.sha, repository.url), problems=['sha', 'repository'])

        target = sha[:12]
        label = message.splitlines()[0]
        label = label[:128]

        project_options = ProjectOptionsHelper.get_options(
            projects, ['build.file-whitelist'])

        collection_id = uuid.uuid4()
        builds = []
        files_changed = self._get_changed_files(repository, revision)
        for project in projects:
            plan_list = get_build_plans(project)
            if not plan_list:
                logging.warning(
                    'No plans defined for project %s', project.slug)
                continue

            if files_changed and not in_project_files_whitelist(project_options[project.id], files_changed):
                logging.info(
                    'No changed files matched build.file-whitelist for project %s', project.slug)
                continue

            # if we get to this point, then a build needs to either exist or be
            # created
            potentials = list(Build.query.filter(
                Build.project_id == project.id,
                Source.revision_sha == sha,
            ).order_by(
                Build.date_created.desc()  # newest first
            ).limit(1))
            if len(potentials) == 0:
                builds.append(create_build(
                    project=project,
                    collection_id=collection_id,
                    sha=sha,
                    target=target,
                    label=label,
                    message=message,
                    author=author,
                ))
            else:
                builds.append(potentials[0])

        return self.respond(builds)
