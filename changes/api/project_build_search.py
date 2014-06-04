from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.constants import Result
from changes.models import Project, Build


class ProjectBuildSearchAPIView(APIView):
    get_parser = reqparse.RequestParser()
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

        if args.source:
            filters.append(Build.target.startswith(args.source))

        if args.query:
            filters.append(or_(
                Build.label.contains(args.query),
                Build.target.startswith(args.query),
            ))

        if args.result:
            filters.append(Build.result == Result[args.result])

        queryset = Build.query.options(
            joinedload('project', innerjoin=True),
            joinedload('author'),
            joinedload('source').joinedload('revision'),
        ).filter(
            Build.project_id == project.id,
            *filters
        ).order_by(Build.date_created.desc())

        return self.paginate(queryset)
