from __future__ import absolute_import, division, unicode_literals

import itertools

from sqlalchemy.orm import joinedload, contains_eager

from changes.api.base import APIView
from changes.constants import Status
from changes.models import Build, Project, Revision, Source


COMMITS_PER_PAGE = 50


class ProjectCommitIndexAPIView(APIView):
    def get(self, project_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        repo = project.repository
        vcs = repo.get_vcs()

        if vcs:
            vcs_log = list(vcs.log(limit=COMMITS_PER_PAGE))

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
        else:
            commits = self.serialize(list(
                Revision.query.options(
                    joinedload('author'),
                ).filter(
                    Revision.repository_id == repo.id,
                ).order_by(Revision.date_created.desc())[:COMMITS_PER_PAGE]
            ))

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

        return self.respond(results)
