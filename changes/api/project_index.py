from __future__ import absolute_import, division, unicode_literals

from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.models import Project, Build


class ProjectIndexAPIView(APIView):
    def get(self):
        queryset = Project.query.order_by(Project.name.asc())

        # queryset = Build.query.options(
        #     joinedload(Build.project),
        #     joinedload(Build.author),
        # ).order_by(Build.date_created.desc(), Build.date_started.desc())
        # if change:
        #     queryset = queryset.filter_by(change=change)

        project_list = list(queryset)

        context = {
            'projects': project_list,
        }

        return self.respond(context)

    def get_stream_channels(self):
        return []
