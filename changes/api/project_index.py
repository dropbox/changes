from __future__ import absolute_import, division, unicode_literals

from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.models import Project, Build


class ProjectIndexAPIView(APIView):
    def get(self):
        queryset = Project.query.order_by(Project.name.asc())

        project_list = list(queryset)

        context = {
            'projects': [],
        }

        for project in project_list:
            data = self.serialize(project)
            data['recentBuilds'] = list(Build.query.options(
                joinedload(Build.project),
                joinedload(Build.author),
            ).filter_by(
                project=project,
            ).order_by(
                Build.date_created.desc(),
            )[:3])

            context['projects'].append(data)

        return self.respond(context)

    def get_stream_channels(self):
        return ['builds:*']
