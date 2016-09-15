from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse, types
from sqlalchemy.orm import contains_eager
from sqlalchemy.sql import func, asc, desc

from changes.api.base import APIView
from changes.constants import Result
from changes.models.bazeltarget import BazelTarget
from changes.models.build import Build
from changes.models.job import Job


SORT_CHOICES = (
    'duration',
    'name'
)

RESULT_CHOICES = [r.name for r in Result] + ['']


class BuildTargetIndexAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('query', type=unicode, location='args')
    parser.add_argument('result', type=unicode, location='args',
                        choices=RESULT_CHOICES)
    parser.add_argument('sort', type=unicode, location='args',
                        choices=SORT_CHOICES, default='duration')
    parser.add_argument('reverse', type=types.boolean, location='args',
                        default=False)

    def get(self, build_id):
        build = Build.query.get(build_id)
        if build is None:
            return self.respond({}, status_code=404)

        args = self.parser.parse_args()

        target_list = BazelTarget.query.options(
            contains_eager('job')
        ).join(
            Job, BazelTarget.job_id == Job.id,
        ).filter(
            Job.build_id == build.id,
        )

        if args.query:
            target_list = target_list.filter(
                func.lower(BazelTarget.name).contains(args.query.lower()),
            )

        if args.result:
            target_list = target_list.filter(
                BazelTarget.result == Result[args.result],
            )

        sort_col, sort_dir = None, None
        if args.sort == 'duration':
            sort_col, sort_dir = BazelTarget.duration, desc
        elif args.sort == 'name':
            sort_col, sort_dir = BazelTarget.name, asc

        if args.reverse:
            sort_dir = {asc: desc, desc: asc}[sort_dir]

        target_list = target_list.order_by(sort_dir(sort_col))

        return self.paginate(target_list, max_per_page=None)
