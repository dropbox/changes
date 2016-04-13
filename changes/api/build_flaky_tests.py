from __future__ import absolute_import

from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.config import db
from changes.constants import Result
from changes.models import Build, Job, TestCase, Source, PhabricatorDiff


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

        if jobs:
            flaky_tests_query = db.session.query(
                TestCase.id,
                TestCase.name,
                TestCase.name_sha,
                TestCase.message,
                TestCase.job_id
            ).filter(
                TestCase.job_id.in_([j.id for j in jobs]),
                TestCase.result == Result.passed,
                TestCase.reruns > 1
            ).order_by(TestCase.name.asc()).all()
        else:
            flaky_tests_query = []

        flaky_tests = []
        for test in flaky_tests_query:
            item = {
                'id': test.id,
                'name': test.name,
                'captured_output': test.message,
                'job_id': test.job_id,
            }

            # Quarantine Keeper only needs the author if there are at most
            # MAX_TESTS_TO_ADD to add. If there are less, it will only send
            # an alert and we don't want to waste time querying the DB
            if len(flaky_tests_query) <= MAX_TESTS_TO_ADD:
                first_build = self._get_first_build(build.project_id, test.name_sha)
                last_test = self._get_last_testcase(build.project_id, test.name_sha)

                possible_authors = [
                    last_test.owner,
                    first_build.author.email,
                ]

                for author in possible_authors:
                    if author:
                        item['author'] = {'email': author}
                        break

                phab_diff = PhabricatorDiff.query.filter(
                    Source.id == first_build.source.id,
                ).first()
                if phab_diff:
                    item['diff_id'] = phab_diff.revision_id

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

    @staticmethod
    def _get_first_build(project_id, test_name_sha):
        """Get the first build (by date created) containing a test case.

        Args:
           :param project_id: string
           :param test_name_sha: string
        Returns:
            Build
        """
        first_test = TestCase.query.filter(
            TestCase.project_id == project_id,
            TestCase.name_sha == test_name_sha,
        ).order_by(TestCase.date_created.asc()).limit(1).first()

        if first_test is None:
            return None

        first_build = Build.query.options(
            joinedload('author'),
            joinedload('source'),
        ).filter(
            Build.id == first_test.job.build_id,
        ).first()
        return first_build

    @staticmethod
    def _get_last_testcase(project_id, test_name_sha):
        """Get the most recent TestCase instance for the specified name.

        Args:
           :param project_id: string
           :param test_name_sha: string
        Returns:
            TestCase
        """
        most_recent_test = TestCase.query.filter(
            TestCase.project_id == project_id,
            TestCase.name_sha == test_name_sha,
        ).order_by(TestCase.date_created.desc()).limit(1).first()
        return most_recent_test
