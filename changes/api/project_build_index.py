from __future__ import absolute_import, division, unicode_literals

from flask_restful.reqparse import RequestParser
from sqlalchemy import or_
from sqlalchemy.orm import contains_eager, joinedload

from changes.api.auth import get_current_user
from changes.api.base import APIView
from changes.constants import Result
from changes.models import Author, Project, Source, Build


def validate_author(author_id):
    current_user = get_current_user()
    if author_id == 'me' and not current_user:
        raise ValueError('You are not authenticated')

    return Author.find(author_id, current_user)


class ProjectBuildIndexAPIView(APIView):
    get_parser = RequestParser()
    get_parser.add_argument('include_patches', type=lambda x: bool(int(x)), location='args',
                            default=True)
    get_parser.add_argument('author', type=validate_author, location='args',
                            dest='authors')
    get_parser.add_argument('query', type=unicode, location='args')
    get_parser.add_argument('source', type=unicode, location='args')
    get_parser.add_argument('result', type=unicode, location='args',
                            choices=('failed', 'passed', 'aborted', 'unknown', ''))

    def get(self, project_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        args = self.get_parser.parse_args()

        filters = []

        if args.authors:
            filters.append(Build.author_id.in_([a.id for a in args.authors]))
        elif args.authors is not None:
            return []

        if args.source:
            filters.append(Build.target.startswith(args.source))

        if args.query:
            filters.append(or_(
                Build.label.contains(args.query),
                Build.target.startswith(args.query),
            ))

        if args.result:
            filters.append(Build.result == Result[args.result])

        if not args.include_patches:
            filters.append(Source.patch_id == None)  # NOQA

        queryset = Build.query.options(
            joinedload('project', innerjoin=True),
            joinedload('author'),
            contains_eager('source').joinedload('revision'),
        ).join(
            Source, Source.id == Build.source_id,
        ).filter(
            Build.project_id == project.id,
            *filters
        ).order_by(Build.date_created.desc())

        return self.paginate(queryset)
