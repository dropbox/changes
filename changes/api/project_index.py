from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse
from sqlalchemy.orm import contains_eager, joinedload

from changes.api.base import APIView
from changes.api.decorators import requires_auth
from changes.config import db
from changes.constants import Status, ProjectStatus
from changes.models import Project, Repository, Build, Source


class ProjectIndexAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('name', type=unicode, required=True)
    parser.add_argument('slug', type=str)
    parser.add_argument('repository', type=unicode, required=True)

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

    @requires_auth
    def post(self):
        args = self.parser.parse_args()

        slug = str(args.slug or args.name.replace(' ', '-').lower())

        match = Project.query.filter(
            Project.slug == slug,
        ).first()
        if match:
            return '{"error": "Project with slug %r already exists"}' % (slug,), 403

        repository = Repository.get(args.repository)
        if repository is None:
            repository = Repository(
                url=args.repository,
            )
            db.session.add(repository)

        project = Project(
            name=args.name,
            slug=slug,
            repository=repository,
        )
        db.session.add(project)

        return self.respond(project)

    def get_stream_channels(self):
        return ['builds:*']
