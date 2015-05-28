#!/usr/bin/env python

from __future__ import absolute_import, print_function

import logging

from datetime import date, timedelta

from changes.config import db
from changes.db.utils import try_create
from changes.lib.flaky_tests import get_flaky_tests
from changes.models import FlakyTestStat, Project


def aggregate_flaky_tests(day=None, max_flaky_tests=200):
    if day is None:
        day = date.today() - timedelta(days=1)

    try:
        projects = Project.query.all()

        for project in projects:
            tests = get_flaky_tests(day, day + timedelta(days=1), [project], max_flaky_tests)

            for test in tests:
                try_create(FlakyTestStat, {
                    'name': test['name'],
                    'project_id': test['project_id'],
                    'date': day,
                    'last_flaky_run_id': test['id'],
                    'flaky_runs': test['flaky_runs'],
                    'passing_runs': test['passing_runs']
                })

        db.session.commit()
    except Exception as err:
        logging.exception(unicode(err))
