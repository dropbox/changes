from __future__ import absolute_import, division, unicode_literals

from sqlalchemy.orm import subqueryload

from changes.api.base import APIView
from changes.models import Build, TestGroup, Job


class BuildTestIndexAPIView(APIView):
    def get(self, build_id):
        build = Build.query.get(build_id)
        if build is None:
            return '', 404

        test_list = list(TestGroup.query.options(
            subqueryload(TestGroup.parent),
        ).join(
            Job, TestGroup.job_id == Job.id,
        ).filter(
            Job.build_id == build.id,
            TestGroup.num_leaves == 0,  # NOQA
        ).order_by(TestGroup.duration.desc()))

        return self.respond(test_list)
