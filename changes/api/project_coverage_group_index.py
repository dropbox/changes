from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse

from changes.api.base import APIView
from changes.config import db
from changes.constants import Result, Status
from changes.models import Build, Job, FileCoverage, Project, Source
from changes.utils.trees import build_tree


SORT_CHOICES = (
    'lines_covered',
    'lines_uncovered',
    'name',
)


class ProjectCoverageGroupIndexAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('parent', type=unicode, location='args')

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
            return '{}'

        # use the most recent coverage
        cover_list = FileCoverage.query.filter(
            FileCoverage.job_id.in_(
                db.session.query(Job.id).filter(
                    Job.build_id == latest_build.id,
                )
            )
        )

        if args.parent:
            cover_list = cover_list.filter(
                FileCoverage.filename.startswith(args.parent),
            )

        cover_list = list(cover_list)

        groups = build_tree(
            [c.filename for c in cover_list],
            sep='/',
            min_children=2,
            parent=args.parent,
        )

        results = []
        for group in groups:
            num_files = 0
            total_lines_covered = 0
            total_lines_uncovered = 0
            for file_coverage in cover_list:
                filename = file_coverage.filename
                if filename == group or filename.startswith(group + '/'):
                    num_files += 1
                    total_lines_covered += file_coverage.lines_covered
                    total_lines_uncovered += file_coverage.lines_uncovered

            if args.parent:
                filename = group[len(args.parent) + len('/'):]
            else:
                filename = group

            data = {
                'filename': filename,
                'path': group,
                'totalLinesCovered': total_lines_covered,
                'totalLinesUncovered': total_lines_uncovered,
                'numFiles': num_files,
            }
            results.append(data)
        results.sort(key=lambda x: x['totalLinesUncovered'], reverse=True)

        trail = []
        context = []
        if args.parent:
            for chunk in args.parent.split('/'):
                context.append(chunk)
                trail.append({
                    'path': '/'.join(context),
                    'name': chunk,
                })

        data = {
            'groups': results,
            'trail': trail,
        }

        return self.respond(data, serialize=False)
