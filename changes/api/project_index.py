from __future__ import absolute_import, division, unicode_literals

from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.constants import Status
from changes.models import Project, Job


class ProjectIndexAPIView(APIView):
    def get(self):
        queryset = Project.query.order_by(Project.name.asc())

        project_list = list(queryset)

        context = {
            'projects': [],
        }

        for project in project_list:
            data = self.serialize(project)
            data['lastBuild'] = Job.query.options(
                joinedload(Job.project),
                joinedload(Job.author),
            ).filter(
                Job.revision_sha != None,  # NOQA
                Job.patch_id == None,
                Job.project == project,
                Job.status == Status.finished,
            ).order_by(
                Job.date_created.desc(),
            ).first()

            context['projects'].append(data)

        return self.respond(context)

    def get_stream_channels(self):
        return ['jobs:*']
