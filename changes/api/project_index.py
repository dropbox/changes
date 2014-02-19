from __future__ import absolute_import, division, unicode_literals

from sqlalchemy.orm import contains_eager, joinedload

from changes.api.base import APIView
from changes.constants import Status, ProjectStatus
from changes.models import Project, Build, Source


class ProjectIndexAPIView(APIView):
    def get(self):
        queryset = Project.query.filter(
            Project.status == ProjectStatus.active,
        ).order_by(Project.name.asc())

        project_list = list(queryset)

        context = []

        for project in project_list:
            data = self.serialize(project)
            data['lastBuild'] = Build.query.options(
                joinedload('project', innerjoin=True),
                joinedload('author'),
                contains_eager('source'),
            ).join(
                Source, Build.source_id == Source.id,
            ).filter(
                Source.patch_id == None,  # NOQA
                Build.project == project,
                Build.status == Status.finished,
            ).order_by(
                Build.date_created.desc(),
            ).first()

            context.append(data)

        return self.paginate(context)

    def get_stream_channels(self):
        return ['builds:*']
