from __future__ import absolute_import, division, unicode_literals

from flask import Response
from sqlalchemy.orm import joinedload, subqueryload

from changes.api.base import APIView
from changes.models import Project, AggregateTestGroup


class ProjectTestDetailsAPIView(APIView):
    def _get_project(self, project_id):
        queryset = Project.query.options(
            joinedload(Project.repository),
        )

        project = queryset.filter_by(slug=project_id).first()
        if project is None:
            project = queryset.get(project_id)
        return project

    def get(self, project_id, test_id):
        project = self._get_project(project_id)
        if not project:
            return Response(status=404)

        queryset = AggregateTestGroup.query.options(
            subqueryload(AggregateTestGroup.first_build),
            subqueryload(AggregateTestGroup.parent),
        )

        test = queryset.get(test_id)
        if test is None:
            return Response(status=404)

        test_list = list(queryset.filter(
            AggregateTestGroup.parent_id == test.id,
            AggregateTestGroup.project_id == project.id,
        ))

        context = {
            'test': test,
            'childTests': test_list,
        }

        return self.respond(context)
