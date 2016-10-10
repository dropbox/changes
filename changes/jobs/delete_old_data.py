from __future__ import absolute_import, print_function

import logging

from datetime import datetime, timedelta

from changes.config import db, statsreporter
from changes.models.project import Project, ProjectOptionsHelper
from changes.models.test import TestCase

DEFAULT_TEST_RETENTION_DAYS = 120
MINIMUM_TEST_RETENTION_DAYS = 7

logger = logging.getLogger('delete-old-data')


def clean_project_tests(project, from_date, chunk_size, num_days=None):
    # type: (Project, datetime, timedelta, int) -> int
    """Deletes old tests from a project and returns number of rows deleted.

    An old test is a test older than num_days or the project's history.test-retention-days
    compared to the `from_date`
    chunk_size bounds how far to back to look from num_days ago to have some control over
    how long this function runs.
    """
    if chunk_size <= timedelta(minutes=0):
        logger.warning('The minutes worth of tests to delete is %s but it must be positive.' %
                       chunk_size)
        return 0
    test_retention_days = num_days or float(
        ProjectOptionsHelper.get_option(project, 'history.test-retention-days') or
        DEFAULT_TEST_RETENTION_DAYS
    )
    if test_retention_days < MINIMUM_TEST_RETENTION_DAYS:
        logger.warning(
            'Test retention days for project %s is %d, which is less than the minimum of %d. '
            'Not cleaning tests for this project.' %
            (project.slug, test_retention_days, MINIMUM_TEST_RETENTION_DAYS))
        return 0

    test_delete_date = from_date - timedelta(days=test_retention_days)
    test_delete_date_limit = test_delete_date - chunk_size

    rows_deleted = db.session.query(TestCase).filter(
        TestCase.project_id == project.id,
        TestCase.date_created < test_delete_date,
        TestCase.date_created >= test_delete_date_limit,
        ).delete()

    db.session.commit()

    statsreporter.stats().incr('count_tests_deleted', rows_deleted)

    return rows_deleted


def delete_old_data_10m():
    # type: () -> None
    delete_old_data_limited(timedelta(minutes=10), datetime.utcnow())


def delete_old_data_5h_delayed():
    # type: () -> None
    delete_old_data_limited(timedelta(hours=5), datetime.utcnow() - timedelta(hours=1))


def delete_old_data_1h():
    # type: () -> None
    delete_old_data_limited(timedelta(hours=1), datetime.utcnow())


def delete_old_data():
    # type: () -> None
    delete_old_data_1h()


def delete_old_data_limited(chunk_size, from_date=None):
    # type: (timedelta, datetime) -> None
    if from_date is None:
        from_date = datetime.utcnow()
    try:
        projects = Project.query.all()

        for project in projects:
            clean_project_tests(project, from_date, chunk_size)
    except Exception as e:
        logger.exception(e.message)
