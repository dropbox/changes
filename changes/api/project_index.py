from __future__ import absolute_import, division, unicode_literals

from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.constants import Status
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
            data['lastBuild'] = Build.query.options(
                joinedload(Build.project),
                joinedload(Build.author),
            ).filter(
                Build.revision_sha != None,  # NOQA
                Build.patch_id == None,
                Build.project == project,
                Build.status == Status.finished,
            ).order_by(
                Build.date_created.desc(),
            ).first()

            data['numActiveBuilds'] = Build.query.filter(
                Build.project == project,
                Build.status != Status.finished,
            ).count()

            context['projects'].append(data)

        return self.respond(context)

    def get_stream_channels(self):
        return ['builds:*']
