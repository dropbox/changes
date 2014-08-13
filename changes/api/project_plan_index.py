from __future__ import absolute_import

from sqlalchemy.orm import subqueryload_all

from changes.models import Project, Plan
from changes.api.base import APIView


class ProjectPlanIndexAPIView(APIView):
    def get(self, project_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        queryset = Plan.query.options(
            subqueryload_all(Plan.steps),
        ).filter(
            Plan.projects.contains(project),
        ).order_by(
            Plan.label.asc(),
        )

        return self.paginate(queryset)
