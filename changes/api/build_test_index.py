from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse, types
from sqlalchemy.orm import contains_eager
from sqlalchemy.sql import func, asc, desc

from changes.api.base import APIView
from changes.constants import Result
from changes.models.build import Build
from changes.models.job import Job
from changes.models.test import TestCase


SORT_CHOICES = (
    'duration',
    'name',
    'retries'
)

RESULT_CHOICES = [r.name for r in Result] + ['']


class BuildTestIndexAPIView(APIView):
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
            return '', 404

        args = self.parser.parse_args()

        test_list = TestCase.query.options(
            contains_eager('job')
        ).join(
            Job, TestCase.job_id == Job.id,
        ).filter(
            Job.build_id == build.id,
        )

        if args.query:
            test_list = test_list.filter(
                func.lower(TestCase.name).contains(args.query.lower()),
            )

        if args.result:
            test_list = test_list.filter(
                TestCase.result == Result[args.result],
            )

        sort_col, sort_dir = None, None
        if args.sort == 'duration':
            sort_col, sort_dir = TestCase.duration, desc
        elif args.sort == 'name':
            sort_col, sort_dir = TestCase.name, asc
        elif args.sort == 'retries':
            sort_col, sort_dir = TestCase.reruns, desc

        if args.reverse:
            sort_dir = {asc: desc, desc: asc}[sort_dir]

        test_list = test_list.order_by(sort_dir(sort_col))

        return self.paginate(test_list, max_per_page=None)
