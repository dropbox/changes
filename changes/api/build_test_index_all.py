from sqlalchemy.orm import contains_eager

from changes.api.base import APIView
from changes.constants import Result
from changes.models import Build, TestCase, Job


class BuildTestIndexAllAPIView(APIView):

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

        result_list = []
        result_counts = {result.name: 0 for result in Result}
        print result_counts

        for test in test_list:
            test_info = dict()
            test_info['name'] = test.name
            test_info['result'] = test.result.name

            result_list.append(test_info)
            result_counts[test.result.name] += 1

        return self.respond({'result_list': result_list, 'result_counts': result_counts})
