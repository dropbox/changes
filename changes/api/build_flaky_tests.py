from __future__ import absolute_import

from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.config import db
from changes.constants import Result
from changes.models import Build, Job, TestCase


# This constant must match MAX_TESTS_TO_ADD in citools' quarantine keeper
MAX_TESTS_TO_ADD = 2


class BuildFlakyTestsAPIView(APIView):
    def get(self, build_id):
        build = Build.query.get(build_id)
        if build is None:
            return '', 404

        jobs = list(Job.query.filter(
            Job.build_id == build.id,
        ))

        flaky_tests_query = db.session.query(
            TestCase.name,
            TestCase.name_sha,
            TestCase.message
        ).filter(
            TestCase.job_id.in_([j.id for j in jobs]),
            TestCase.result == Result.passed,
            TestCase.reruns > 1
        ).order_by(TestCase.name.asc()).all()

        flaky_tests = []
        for test in flaky_tests_query:
            item = {
                'name': test.name,
                'captured_output': test.message,
            }

            # Quarantine Keeper only needs the author if there are at most
            # MAX_TESTS_TO_ADD to add. If there are less, it will only send
            # an alert and we don't want to waste time querying the DB
            if len(flaky_tests_query) <= MAX_TESTS_TO_ADD:
                first_test = TestCase.query.filter(
                    TestCase.project_id == build.project_id,
                    TestCase.name_sha == test.name_sha,
                ).order_by(TestCase.date_created.asc()).limit(1).first()

                first_build = Build.query.options(
                    joinedload('author'),
                    joinedload('source'),
                ).filter(
                    Build.id == first_test.job.build_id,
                ).first()

                item['author'] = {'email': first_build.author.email}

                if first_build.source.patch_id:
                    # Use Phabricator revision ID without trailing D
                    item['diff_id'] = first_build.target[1:]

            flaky_tests.append(item)

        context = {
            'projectSlug': build.project.slug,
            'repositoryUrl': build.project.repository.url,
            'flakyTests': {
                'count': len(flaky_tests),
                'items': flaky_tests
            }
        }

        return self.respond(context)
