from __future__ import absolute_import, division, unicode_literals

import itertools

from flask import Response
from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.models import Project, Build, Revision


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

        commits = Revision.query.filter(
            Revision.repository_id == repo.id,
        ).join(Revision.author).order_by(Revision.date_created.desc())[:100]

        builds_qs = list(Build.query.filter(
            Build.project_id == project.id,
            Build.revision_sha.in_(c.sha for c in commits),
            Build.patch == None,  # NOQA
        ).order_by(Build.date_created.asc()))

        builds_map = dict(
            (b.revision_sha, d)
            for b, d in itertools.izip(builds_qs, self.serialize(builds_qs))
        )

        results = []
        for (commit, data) in itertools.izip(commits, self.serialize(commits)):
            data['build'] = builds_map.get(commit.sha)
            results.append(data)

        context = {
            'commits': results,
        }

        return self.respond(context)
