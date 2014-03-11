from __future__ import absolute_import, division, unicode_literals

from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.models import Build, Project, Revision, Source


class ProjectCommitDetailsAPIView(APIView):
    def get(self, project_id, commit_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        repo = project.repository
        revision = Revision.query.filter(
            Revision.repository_id == repo.id,
            Revision.sha == commit_id,
        ).join(Revision.author).first()
        if not revision:
            return '', 404

        build_list = list(Build.query.options(
            joinedload('author'),
            joinedload('source'),
        ).filter(
            Build.project_id == project.id,
            Source.revision_sha == revision.sha,
            Source.patch == None,  # NOQA
        ).order_by(Build.date_created.desc()))[:100]

        context = self.serialize(revision)

        context.update({
            'repository': repo,
            'builds': build_list,
        })

        return self.respond(context)

    def get_stream_channels(self, project_id, commit_id):
        return [
            'revisions:{0}:*'.format(commit_id),
        ]
