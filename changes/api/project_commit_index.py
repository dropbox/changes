from __future__ import absolute_import, division, unicode_literals

import itertools

from flask import Response
from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.constants import Status
from changes.models import Build, Project, Revision, Source


class ProjectCommitIndexAPIView(APIView):
    def _get_project(self, project_id):
        project = Project.query.options(
            joinedload(Project.repository),
        ).filter_by(slug=project_id).first()
        if project is None:
            project = Project.query.options(
                joinedload(Project.repository),
            ).get(project_id)
        return project

    def get(self, project_id):
        project = self._get_project(project_id)
        if not project:
            return Response(status=404)

        repo = project.repository
        vcs = repo.get_vcs()

        if vcs:
            vcs_log = list(vcs.log())

            revisions_qs = list(Revision.query.filter(
                Revision.repository_id == repo.id,
                Revision.sha.in_(c.id for c in vcs_log)
            ).join(Revision.author))

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
            commits = self.serialize(list(
                Revision.query.filter(
                    Revision.repository_id == repo.id,
                ).join(
                    Revision.author,
                ).order_by(Revision.date_created.desc())[:100]
            ))

        builds_qs = list(Build.query.options(
            joinedload('author'),
        ).filter(
            Build.source_id == Source.id,
            Build.project_id == project.id,
            Build.status.in_([Status.finished, Status.in_progress]),
            Source.revision_sha.in_(c['id'] for c in commits),
            Source.patch == None,  # NOQA
        ).order_by(Build.date_created.asc()))

        builds_map = dict(
            (b.source.revision_sha, d)
            for b, d in itertools.izip(builds_qs, self.serialize(builds_qs))
        )

        results = []
        for result in commits:
            result['build'] = builds_map.get(result['id'])
            results.append(result)

        context = {
            'commits': results,
        }

        return self.respond(context)
