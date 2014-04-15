from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse
from sqlalchemy.orm import contains_eager

from changes.api.base import APIView
from changes.models import Build, TestCase, Job


SORT_CHOICES = (
    'duration',
    'name',
    'retries'
)


class BuildTestIndexAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('sort', type=unicode, location='args',
                        choices=SORT_CHOICES, default='duration')

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

        if args.sort == 'duration':
            sort_by = TestCase.duration.desc()
        elif args.sort == 'name':
            sort_by = TestCase.name.asc()
        elif args.sort == 'retries':
            sort_by = TestCase.reruns.desc()

        test_list = test_list.order_by(sort_by)

        return self.paginate(test_list)
