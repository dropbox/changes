from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse
from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.models.latest_green_build import LatestGreenBuild
from changes.models.project import Project


class ProjectLatestGreenBuildsAPIView(APIView):
    get_parser = reqparse.RequestParser()
    get_parser.add_argument('branch', type=unicode, location='args')

    def get(self, project_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        args = self.get_parser.parse_args()

        filters = []

        if args.branch:
            filters.append(LatestGreenBuild.branch == args.branch)

        queryset = LatestGreenBuild.query.options(
            joinedload('build').joinedload('source').joinedload('revision')
        ).filter(
            LatestGreenBuild.project_id == project.id,
            *filters
        )

        return self.paginate(queryset)
