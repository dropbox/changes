from flask import Response
from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.models import Project


class ProjectDetailsAPIView(APIView):
    def get(self, project_id):
        project = Project.query.options(
            joinedload(Project.repository),
        ).get(project_id)
        if project is None:
            return Response(status=404)

        context = {
            'project': project,
        }

        return self.respond(context)
