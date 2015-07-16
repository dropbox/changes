from __future__ import absolute_import

from changes.api.base import APIView
from changes.config import db
from changes.constants import Result
from changes.models import Build, Job, TestCase


class BuildFlakyTestsAPIView(APIView):
    def get(self, build_id):
        build = Build.query.get(build_id)
        if build is None:
            return '', 404

        jobs = list(Job.query.filter(
            Job.build_id == build.id,
        ))

        flaky_tests_query = db.session.query(
            TestCase.name
        ).filter(
            TestCase.job_id.in_([j.id for j in jobs]),
            TestCase.result == Result.passed,
            TestCase.reruns > 1
        ).order_by(TestCase.name.asc())

        flaky_tests = map(lambda test: {'name': test.name}, flaky_tests_query)

        context = {
            'repositoryUrl': build.project.repository.url,
            'flakyTests': {
                'count': len(flaky_tests),
                'items': flaky_tests
            }
        }

        return self.respond(context)
