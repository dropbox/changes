from __future__ import absolute_import, division, unicode_literals

import itertools

from flask.ext.restful import reqparse
from sqlalchemy.orm import joinedload, contains_eager

from changes.api.base import APIView
from changes.constants import Cause, Status
from changes.models import Build, Project, Revision, Source


class ProjectCommitIndexAPIView(APIView):
    get_parser = reqparse.RequestParser()
    get_parser.add_argument('page', type=int, location='args',
                            default=1)
    get_parser.add_argument('per_page', type=int, location='args',
                            default=50)
    get_parser.add_argument('parent', location='args')

    def get(self, project_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        args = self.get_parser.parse_args()

        repo = project.repository
        vcs = repo.get_vcs()

        offset = (args.page - 1) * args.per_page
        limit = args.per_page + 1

        if vcs:
            vcs_log = list(vcs.log(
                offset=offset,
                limit=limit,
                parent=args.parent,
            ))

            if vcs_log:
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
            else:
                commits = []
        elif args.parent:
            return '{"error": "Parent argument not supported"}', 400
        else:
            commits = self.serialize(list(
                Revision.query.options(
                    joinedload('author'),
                ).filter(
                    Revision.repository_id == repo.id,
                ).order_by(Revision.date_created.desc())[offset:offset + limit]
            ))

        page_links = self.make_links(
            current_page=args.page,
            has_next_page=len(commits) > args.per_page,
        )

        commits = commits[:args.per_page]

        if commits:
            builds_qs = list(Build.query.options(
                joinedload('author'),
                contains_eager('source'),
            ).join(
                Source, Source.id == Build.source_id,
            ).filter(
                Build.source_id == Source.id,
                Build.project_id == project.id,
                Build.status.in_([Status.finished, Status.in_progress, Status.queued]),
                Build.cause != Cause.snapshot,
                Source.revision_sha.in_(c['id'] for c in commits),
                Source.patch == None,  # NOQA
            ).order_by(Build.date_created.asc()))

            builds_map = dict(
                (b.source.revision_sha, d)
                for b, d in itertools.izip(builds_qs, self.serialize(builds_qs))
            )
        else:
            builds_map = {}

        results = []
        for result in commits:
            result['build'] = builds_map.get(result['id'])
            results.append(result)

        return self.respond(results, links=page_links)
