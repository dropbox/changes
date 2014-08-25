from __future__ import absolute_import, division, unicode_literals

from flask_restful.reqparse import RequestParser
from sqlalchemy.orm import contains_eager, joinedload

from changes.api.auth import get_current_user
from changes.api.base import APIView
from changes.models import Author, Project, Source, Build


def validate_author(author_id):
    current_user = get_current_user()
    if author_id == 'me' and not current_user:
        raise ValueError('You are not authenticated')

    return Author.find(author_id, current_user)


class ProjectBuildIndexAPIView(APIView):
    get_parser = RequestParser()
    get_parser.add_argument('include_patches', type=bool, location='args',
                            default=True)
    get_parser.add_argument('author', type=validate_author, location='args',
                            dest='authors')

    def get(self, project_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        args = self.get_parser.parse_args()

        queryset = Build.query.options(
            joinedload('project'),
            joinedload('author'),
            contains_eager('source').joinedload('revision'),
        ).join(
            Source, Source.id == Build.source_id,
        ).filter(
            Build.project_id == project.id,
        ).order_by(Build.date_created.desc())

        if args.authors:
            queryset = queryset.filter(
                Build.author_id.in_([a.id for a in args.authors]),
            )
        elif args.authors is not None:
            return []

        if args.include_patches:
            queryset = queryset.filter(
                Source.patch_id == None,  # NOQA
            )

        return self.paginate(queryset)
