from __future__ import absolute_import, division, unicode_literals

from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.models import Project, Source


class ProjectSourceDetailsAPIView(APIView):
    def _get_project(self, project_id):
        project = Project.query.options(
            joinedload(Project.repository, innerjoin=True),
        ).filter_by(slug=project_id).first()
        if project is None:
            project = Project.query.options(
                joinedload(Project.repository, innerjoin=True),
            ).get(project_id)
        return project

    def get(self, project_id, source_id):
        project = self._get_project(project_id)
        if not project:
            return '', 404

        repo = project.repository
        source = Source.query.filter(
            Source.id == source_id,
            Source.repository_id == repo.id,
        ).first()
        if source is None:
            return '', 404

        context = self.serialize(source)

        if source.patch:
            context['diff'] = source.patch.diff
        else:
            vcs = repo.get_vcs()
            if vcs:
                context['diff'] = vcs.export(source.revision_sha)
            else:
                context['diff'] = None

        return self.respond(context)
