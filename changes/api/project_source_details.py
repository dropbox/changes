from __future__ import absolute_import, division, unicode_literals

from changes.api.base import APIView
from changes.models import Project, Source


class ProjectSourceDetailsAPIView(APIView):
    def get(self, project_id, source_id):
        project = Project.get(project_id)
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
                try:
                    context['diff'] = vcs.export(source.revision_sha)
                except Exception:
                    context['diff'] = None
            else:
                context['diff'] = None

        return self.respond(context)
