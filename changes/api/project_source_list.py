from datetime import datetime, timedelta

from changes.api.base import APIView
from changes.models import Project, Source


class ProjectSourceListAPIView(APIView):
    def get(self, project_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        repo = project.repository
        sources = Source.query.filter(
            Source.repository_id == repo.id,
            Source.date_created > datetime.today() - timedelta(days=1),
        ).order_by(Source.date_created.desc())

        response = self.serialize([source.id for source in sources])
        return self.respond(response)
