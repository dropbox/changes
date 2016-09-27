from __future__ import absolute_import, division, unicode_literals

import itertools
from collections import defaultdict

from flask.ext.restful import reqparse
from sqlalchemy.orm import joinedload, contains_eager

from changes.api.base import APIView, error
from changes.constants import Status
from changes.lib import build_type
from changes.models.build import Build
from changes.models.project import Project, ProjectOptionsHelper
from changes.models.revision import Revision
from changes.models.revisionresult import RevisionResult
from changes.models.source import Source


class ProjectCommitIndexAPIView(APIView):
    get_parser = reqparse.RequestParser()
    get_parser.add_argument('page', type=int, location='args',
                            default=1)
    get_parser.add_argument('per_page', type=int, location='args',
                            default=50)
    get_parser.add_argument('parent', location='args')
    get_parser.add_argument('branch', location='args')
    get_parser.add_argument('every_commit', location='args', default=0)
    get_parser.add_argument('all_builds', location='args', default=0)

    def get(self, project_id):
        project = Project.get(project_id)
        if not project:
            return error('project not found', http_code=404)

        args = self.get_parser.parse_args()

        # we want to only return commits in the repo that are within the
        # project's whitelist
        paths = None
        if not args.every_commit:
            paths = ProjectOptionsHelper.get_whitelisted_paths(project)

        repo = project.repository
        offset = (args.page - 1) * args.per_page
        limit = args.per_page + 1  # +1 to tell if there are more revs to get

        vcs = repo.get_vcs()
        if vcs:
            try:
                commits = self.get_commits_from_vcs(
                    repo, vcs, offset, limit, paths, args.parent, args.branch)
            except ValueError as err:
                return error(err.message)
        else:
            if args.parent or args.branch:
                param = 'Branches' if args.branch else 'Parents'
                return error(
                    '{0} not supported for projects with no repository.'.format(param),
                    http_code=422)
            # TODO: right now this fallback returns every commit for projects
            # with whitelisted paths.  At the very least, we need to tell the
            # frontend about this (perhaps using a response header)
            commits = self.get_commits_from_db(repo, offset, limit)

        page_links = self.make_links(
            current_page=args.page,
            has_next_page=len(commits) > args.per_page,
        )
        # we fetched one extra commit so that we'd know whether to create a
        # next link. Delete it
        commits = commits[:args.per_page]

        builds_map = {}
        if commits:
            builds_map = self.get_builds_for_commits(
                commits, project, args.all_builds)

        revision_result_map = self.get_revision_result_map(project, [c['id'] for c in commits])

        results = []
        for result in commits:
            if args.all_builds:
                result['builds'] = builds_map.get(result['id'], [])
            else:
                result['build'] = builds_map.get(result['id'])
            if result['id'] in revision_result_map:
                result['revisionResult'] = self.serialize(revision_result_map[result['id']])
            results.append(result)

        return self.respond(results, serialize=False, links=page_links)

    def get_revision_result_map(self, project, shas):
        revision_results = RevisionResult.query.filter(
            RevisionResult.revision_sha.in_(shas),
            RevisionResult.project_id == project.id,
        )
        result_map = {}
        for result in revision_results:
            result_map[result.revision_sha] = result
        return result_map

    def get_commits_from_vcs(self, repo, vcs, offset, limit, paths, parent, branch):
        vcs_log = list(vcs.log(
            offset=offset,
            limit=limit,
            parent=parent,
            branch=branch,
            paths=paths
        ))

        if not vcs_log:
            return []

        revisions_qs = list(Revision.query.options(
            joinedload('author'),
        ).filter(
            Revision.repository_id == repo.id,
            Revision.sha.in_(c.id for c in vcs_log)
        ))

        revisions_map = dict(
            (c.sha, d)
            for c, d in itertools.izip(revisions_qs, self.serialize(revisions_qs))
        )

        commits = []
        for commit in vcs_log:
            if commit.id in revisions_map:
                result = revisions_map[commit.id]
            else:
                result = self.serialize(commit)
            commits.append(result)
        return commits

    def get_commits_from_db(self, repo, offset, limit):
        return self.serialize(list(
            Revision.query.options(
                joinedload('author'),
            ).filter(
                Revision.repository_id == repo.id,
            ).order_by(Revision.date_created.desc())[offset:offset + limit]
        ))

    def get_builds_for_commits(self, commits, project, all_builds):
        builds_qs = list(Build.query.options(
            joinedload('author'),
            contains_eager('source'),
        ).join(
            Source, Source.id == Build.source_id,
        ).filter(
            Build.source_id == Source.id,
            Build.project_id == project.id,
            Build.status.in_([Status.finished, Status.in_progress, Status.queued]),
            Source.repository_id == project.repository_id,
            Source.revision_sha.in_(c['id'] for c in commits),
            *build_type.get_any_commit_build_filters()
        ).order_by(Build.date_created.asc()))

        if not all_builds:
            # this implicitly only keeps the last build for a revision
            return dict(
                (b.source.revision_sha, d)
                for b, d in itertools.izip(builds_qs, self.serialize(builds_qs))
            )
        else:
            builds_map = defaultdict(list)
            for b, d in itertools.izip(builds_qs, self.serialize(builds_qs)):
                builds_map[b.source.revision_sha].append(d)
            return dict(builds_map)
