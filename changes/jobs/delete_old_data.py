from __future__ import absolute_import, print_function

import logging

from datetime import datetime, timedelta

from changes.config import db
from changes.models.project import Project, ProjectOptionsHelper
from changes.models.test import TestCase

DEFAULT_TEST_RETENTION_DAYS = 60


def clean_project_tests(project, current_date):
    test_retention_days = float(ProjectOptionsHelper.get_option(project, 'history.test-retention-days')) \
                          or DEFAULT_TEST_RETENTION_DAYS
    test_delete_date = current_date - timedelta(days=test_retention_days)

    rows_deleted = db.session.query(TestCase).filter(
        TestCase.project_id == project.id,
        TestCase.date_created < test_delete_date,
        ).delete()

    db.session.commit()

    return rows_deleted


def delete_old_data(current_date=None):
    if current_date is None:
        current_date = datetime.utcnow()
    try:
        projects = Project.query.all()

        for project in projects:
            clean_project_tests(project, current_date)
    except Exception as e:
        logging.exception(e.message)
