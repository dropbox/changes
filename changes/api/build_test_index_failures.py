from sqlalchemy.orm import contains_eager

from changes.api.base import APIView
from changes.constants import Result
from changes.models import Build, TestCase, Job


class BuildTestIndexFailuresAPIView(APIView):

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
            TestCase.result != Result.passed,
        )

        result_list = []

        for test in test_list:
            test_info = dict()
            test_info['name'] = test.name
            test_info['hash'] = test.name_sha
            test_info['result'] = test.result.name
            test_info['job_id'] = test.job_id
            test_info['test_id'] = test.id
            test_info['shortName'] = test.short_name

            result_list.append(test_info)

        return self.respond(result_list)
