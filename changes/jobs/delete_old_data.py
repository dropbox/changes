from __future__ import absolute_import, print_function

import logging

from datetime import datetime, timedelta

from changes.config import db, statsreporter
from changes.models.project import Project, ProjectOptionsHelper
from changes.models.test import TestCase

DEFAULT_TEST_RETENTION_DAYS = 120
MINIMUM_TEST_RETENTION_DAYS = 7

logger = logging.getLogger('delete-old-data')


def clean_project_tests(project, current_date, num_days=None):
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
    test_delete_date = current_date - timedelta(days=test_retention_days)

    rows_deleted = db.session.query(TestCase).filter(
        TestCase.project_id == project.id,
        TestCase.date_created < test_delete_date,
        ).delete()

    db.session.commit()

    statsreporter.stats().incr('count_tests_deleted', rows_deleted)

    return rows_deleted


def delete_old_data(current_date=None):
    if current_date is None:
        current_date = datetime.utcnow()
    try:
        projects = Project.query.all()

        for project in projects:
            clean_project_tests(project, current_date)
    except Exception as e:
        logger.exception(e.message)
