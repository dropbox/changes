from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse

from changes.api.base import APIView
from changes.constants import Result, Status
from changes.models import Build, Job, FileCoverage, Project, Source

SORT_CHOICES = (
    'lines_covered',
    'lines_uncovered',
    'name',
)


class ProjectCoverageIndexAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('query', type=unicode, location='args')
    parser.add_argument('sort', type=unicode, location='args',
                        choices=SORT_CHOICES, default='name')

    def get(self, project_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        args = self.parser.parse_args()

        latest_build = Build.query.join(
            Source, Source.id == Build.source_id,
        ).filter(
            Source.patch_id == None,  # NOQA
            Build.project_id == project.id,
            Build.result == Result.passed,
            Build.status == Status.finished,
        ).order_by(
            Build.date_created.desc(),
        ).limit(1).first()

        if not latest_build:
            return self.respond([])

        # use the most recent coverage
        cover_list = FileCoverage.query.filter(
            FileCoverage.job_id.in_(
                Job.query.filter(Job.build_id == latest_build.id)
            )
        )

        if args.query:
            cover_list = cover_list.filter(
                FileCoverage.filename.startswith(args.query),
            )

        if args.sort == 'lines_covered':
            sort_by = FileCoverage.lines_covered.desc()
        elif args.sort == 'lines_covered':
            sort_by = FileCoverage.lines_uncovered.desc()
        elif args.sort == 'name':
            sort_by = FileCoverage.name.asc()

        cover_list = cover_list.order_by(sort_by)

        return self.paginate(cover_list)
