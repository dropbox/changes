from sqlalchemy.orm import contains_eager

from changes.api.base import APIView
from changes.constants import Result
from changes.models.build import Build
from changes.models.job import Job
from changes.models.test import TestCase


class BuildTestIndexCountsAPIView(APIView):

    def get(self, build_id):
        build = Build.query.get(build_id)
        if build is None:
            return '', 404

        test_list = TestCase.query.options(
            contains_eager('job')
        ).join(
            Job, TestCase.job_id == Job.id,
        ).filter(
            Job.build_id == build.id,
        )

        count_dict = {result.name: 0 for result in Result}

        for test in test_list:
            count_dict[test.result.name] += 1

        return self.respond(count_dict)
