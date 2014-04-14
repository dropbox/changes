from __future__ import absolute_import, division, unicode_literals

from sqlalchemy.orm import contains_eager

from changes.api.base import APIView
from changes.models import Build, TestCase, Job


class BuildTestIndexAPIView(APIView):
    def get(self, build_id):
        build = Build.query.get(build_id)
        if build is None:
            return '', 404

        test_list = list(TestCase.query.options(
            contains_eager('job')
        ).join(
            Job, TestCase.job_id == Job.id,
        ).filter(
            Job.build_id == build.id,
        ).order_by(TestCase.duration.desc()))

        return self.paginate(test_list)
