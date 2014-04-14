from __future__ import absolute_import, division

import re

from datetime import datetime
from sqlalchemy import and_
from sqlalchemy.sql import func, select

from changes.config import db
from changes.constants import Result
from changes.db.utils import create_or_update, try_create
from changes.models import ItemStat, Job, TestCase


class TestResult(object):
    """
    A helper class which ensures that TestSuite instances are
    managed correctly when TestCase's are created.
    """
    def __init__(self, step, name, message=None, package=None,
                 result=None, duration=None, date_created=None, suite=None,
                 reruns=None):
        self.step = step
        self._name = name
        self._package = package
        self.message = message
        self.result = result or Result.unknown
        self.duration = duration  # ms
        self.date_created = date_created or datetime.utcnow()
        self.suite = suite
        self.reruns = reruns

    @property
    def sep(self):
        name = (self._package or self._name)
        # handle the case where it might begin with some special character
        if not re.match(r'^[a-zA-Z0-9]', name):
            return '/'
        elif '/' in name:
            return '/'
        return '.'

    @property
    def name_sha(self):
        return TestCase.calculate_name_sha(self.name)

    @property
    def package(self):
        return None

    @property
    def name(self):
        if self._package:
            return "%s%s%s" % (self._package, self.sep, self._name)
        return self._name
    id = name


class TestResultManager(object):
    def __init__(self, step):
        self.step = step

    def clear(self):
        """
        Removes all existing test data from this job.
        """
        TestCase.query.filter(
            TestCase.step_id == self.step.id,
        ).delete(synchronize_session=False)

    def save(self, test_list):
        step = self.step
        job = step.job
        project = job.project
        # agg_groups_by_id = {}

        # create all test cases
        for test in test_list:
            testcase = TestCase(
                job=job,
                step=step,
                name_sha=test.name_sha,
                project=project,
                suite=test.suite,
                name=test.name,
                duration=test.duration,
                message=test.message,
                result=test.result,
                date_created=test.date_created,
                reruns=test.reruns
            )
            db.session.add(testcase)

        db.session.commit()

        test_count = TestCase.query.filter(
            TestCase.job_id == job.id,
        ).count()

        create_or_update(ItemStat, where={
            'item_id': job.id,
            'name': 'test_count',
        }, values={
            'value': test_count,
        })

        instance = try_create(ItemStat, where={
            'item_id': job.build_id,
            'name': 'test_count',
        }, defaults={
            'value': test_count
        })
        if not instance:
            ItemStat.query.filter(
                ItemStat.item_id == job.build_id,
                ItemStat.name == 'test_count',
            ).update({
                'value': select([func.sum(ItemStat.value)]).where(
                    and_(
                        ItemStat.name == 'test_count',
                        ItemStat.item_id.in_(select([Job.id]).where(
                            Job.build_id == job.build_id,
                        ))
                    )
                ),
            }, synchronize_session=False)
