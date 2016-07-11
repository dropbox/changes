from __future__ import absolute_import

from datetime import datetime, timedelta

from changes.models.test import TestCase
from changes.jobs.delete_old_data import clean_project_tests
from changes.testutils import TestCase as BaseTestCase


class DeleteOldDataTest(BaseTestCase):
    def test_clean_project_tests(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)

        self.create_project_option(project, 'history.test-retention-days', 10)

        current_date = datetime(2016, 1, 1)
        old_test = self.create_test(job, date_created=current_date - timedelta(days=11))
        new_test = self.create_test(job, date_created=current_date - timedelta(days=9))

        rows_deleted = clean_project_tests(project, current_date)
        assert rows_deleted == 1

        cases = TestCase.query.filter_by(
            project_id=project.id,
        ).all()

        assert len(cases) == 1
        assert cases[0].id == new_test.id

    def test_clean_project_tests_default(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)

        # Don't set test-retention-days

        current_date = datetime(2016, 1, 1)
        old_test = self.create_test(job, date_created=current_date - timedelta(days=121))
        new_test = self.create_test(job, date_created=current_date - timedelta(days=119))

        rows_deleted = clean_project_tests(project, current_date)
        assert rows_deleted == 1

        cases = TestCase.query.filter_by(
            project_id=project.id,
        ).all()

        assert len(cases) == 1
        assert cases[0].id == new_test.id

    def test_clean_project_tests_minimum(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)

        # Set test-retention-days below the minimum. No tests should be processed
        self.create_project_option(project, 'history.test-retention-days', 6)

        current_date = datetime(2016, 1, 1)
        old_test = self.create_test(job, date_created=current_date - timedelta(days=1))
        new_test = self.create_test(job, date_created=current_date - timedelta(days=10))

        rows_deleted = clean_project_tests(project, current_date)
        assert rows_deleted == 0

        cases = TestCase.query.filter_by(
            project_id=project.id,
        ).all()

        assert len(cases) == 2
