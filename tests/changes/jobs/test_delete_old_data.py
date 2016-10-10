from __future__ import absolute_import

from datetime import datetime, timedelta

from changes.models.test import TestCase
from changes.jobs.delete_old_data import clean_project_tests
from changes.testutils import TestCase as BaseTestCase


class DeleteOldDataTest(BaseTestCase):
    def test_clean_project_tests(self):
        # type: () -> None
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)

        self.create_project_option(project, 'history.test-retention-days', 10)

        current_date = datetime(2016, 1, 1)
        old_test = self.create_test(job, date_created=current_date - timedelta(days=11))
        new_test = self.create_test(job, date_created=current_date - timedelta(days=9))

        rows_deleted = clean_project_tests(project, current_date, timedelta(days=3))
        assert rows_deleted == 1

        cases = TestCase.query.filter_by(
            project_id=project.id,
        ).all()

        assert len(cases) == 1
        assert cases[0].id == new_test.id

    def test_clean_project_tests_default(self):
        # type: () -> None
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)

        # Don't set test-retention-days

        current_date = datetime(2016, 1, 1)
        old_test = self.create_test(job, date_created=current_date - timedelta(days=121))
        new_test = self.create_test(job, date_created=current_date - timedelta(days=119))

        rows_deleted = clean_project_tests(project, current_date, timedelta(days=3))
        assert rows_deleted == 1

        cases = TestCase.query.filter_by(
            project_id=project.id,
        ).all()

        assert len(cases) == 1
        assert cases[0].id == new_test.id

    def test_clean_project_tests_timebound(self):
        # type: () -> None
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)

        current_date = datetime(2016, 1, 1)
        expected_cleaned = set([
            self.create_test(job, date_created=current_date - timedelta(days=11)).id,
            self.create_test(job, date_created=current_date - timedelta(days=12)).id,
            self.create_test(job, date_created=current_date - timedelta(days=13)).id,
        ])
        expected_kept = set([
            self.create_test(job, date_created=current_date - timedelta(days=9)).id,
            self.create_test(job, date_created=current_date - timedelta(days=20)).id,
        ])

        rows_deleted = clean_project_tests(project, current_date,
                                           timedelta(days=5), num_days=10)
        assert rows_deleted == len(expected_cleaned)

        cases = TestCase.query.filter_by(
            project_id=project.id,
        ).all()

        assert len(cases) == len(expected_kept)
        for c in cases:
            assert c.id in expected_kept

    def test_clean_project_tests_minimum(self):
        # type: () -> None
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)

        # Set test-retention-days below the minimum. No tests should be processed
        self.create_project_option(project, 'history.test-retention-days', 6)

        current_date = datetime(2016, 1, 1)
        old_test = self.create_test(job, date_created=current_date - timedelta(days=1))
        new_test = self.create_test(job, date_created=current_date - timedelta(days=10))

        rows_deleted = clean_project_tests(project, current_date, timedelta(days=10))
        assert rows_deleted == 0

        cases = TestCase.query.filter_by(
            project_id=project.id,
        ).all()

        assert len(cases) == 2
