from __future__ import absolute_import, division

import logging
import re

from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import func

from changes.config import db
from changes.constants import Result
from changes.db.utils import create_or_update
from changes.models import ItemStat, TestCase, TestArtifact

logger = logging.getLogger('changes.testresult')


class TestResult(object):
    """
    A helper class which ensures that TestSuite instances are
    managed correctly when TestCase's are created.
    """
    def __init__(self, step, name, message=None, package=None,
                 result=None, duration=None, date_created=None,
                 reruns=None, artifacts=None):
        self.step = step
        self._name = name
        self._package = package
        self.message = message
        self.result = result or Result.unknown
        self.duration = duration  # ms
        self.date_created = date_created or datetime.utcnow()
        self.reruns = reruns or 0
        self.artifacts = artifacts

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
        if not test_list:
            return

        step = self.step
        job = step.job
        project = job.project

        # Create all test cases.
        testcase_list = []

        for test in test_list:
            testcase = TestCase(
                job=job,
                step=step,
                name_sha=test.name_sha,
                project=project,
                name=test.name,
                duration=test.duration,
                message=test.message,
                result=test.result,
                date_created=test.date_created,
                reruns=test.reruns
            )
            testcase_list.append(testcase)

        # Try an optimistic commit of all cases at once.
        for testcase in testcase_list:
            db.session.add(testcase)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()

            # Slowly make separate commits, to uncover duplicate test cases:
            for i, testcase in enumerate(testcase_list):
                db.session.add(testcase)
                try:
                    db.session.commit()
                except IntegrityError:
                    db.session.rollback()
                    testcase_list[i] = _update_duplicate(testcase)
                    db.session.commit()

        # Test artifacts do not operate under a unique constraint, so
        # they should insert cleanly without an integrity error.

        for test, testcase in zip(test_list, testcase_list):
            if test.artifacts:
                for ta in test.artifacts:
                    testartifact = TestArtifact(
                        name=ta['name'],
                        type=ta['type'],
                        test=testcase,)
                    testartifact.save_base64_content(ta['base64'])
                    db.session.add(testartifact)

        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            logger.exception('Failed to save artifacts'
                             ' for step {}'.format(step.id.hex))

        try:
            self._record_test_counts()
            self._record_test_failures()
            self._record_test_duration()
            self._record_test_rerun_counts()
        except Exception:
            db.session.rollback()
            logger.exception('Failed to record aggregate test statistics'
                             ' for step {}'.format(step.id.hex))

    def _record_test_counts(self):
        create_or_update(ItemStat, where={
            'item_id': self.step.id,
            'name': 'test_count',
        }, values={
            'value': db.session.query(func.count(TestCase.id)).filter(
                TestCase.step_id == self.step.id,
            ).as_scalar(),
        })
        db.session.commit()

    def _record_test_failures(self):
        create_or_update(ItemStat, where={
            'item_id': self.step.id,
            'name': 'test_failures',
        }, values={
            'value': db.session.query(func.count(TestCase.id)).filter(
                TestCase.step_id == self.step.id,
                TestCase.result == Result.failed,
            ).as_scalar(),
        })
        db.session.commit()

    def _record_test_duration(self):
        create_or_update(ItemStat, where={
            'item_id': self.step.id,
            'name': 'test_duration',
        }, values={
            'value': db.session.query(func.coalesce(func.sum(TestCase.duration), 0)).filter(
                TestCase.step_id == self.step.id,
            ).as_scalar(),
        })

    def _record_test_rerun_counts(self):
        create_or_update(ItemStat, where={
            'item_id': self.step.id,
            'name': 'test_rerun_count',
        }, values={
            'value': db.session.query(func.count(TestCase.id)).filter(
                TestCase.step_id == self.step.id,
                TestCase.reruns > 0,
            ).as_scalar(),
        })


def _update_duplicate(testcase):
    """Find the duplicate that already exists for `testcase` and update it."""
    filter_by = TestCase.query.filter_by
    matches = filter_by(job_id=testcase.job_id, name_sha=testcase.name_sha)
    duplicate = matches.limit(1).first()

    if duplicate.step is testcase.step:
        duplicate.message = ('Duplicate test - ran twice in step {}'
                             .format(testcase.step.label))
        duplicate.duration += testcase.duration or 0
        duplicate.reruns += testcase.reruns or 0
    else:
        duplicate.message = ('Duplicate test - ran in both steps {} and {}'
                             .format(duplicate.step.label, testcase.step.label))

        # The duplicate - the only copy that can exist - must now be
        # moved over to the new step, for when its stats are tallied:
        duplicate.step = testcase.step
        duplicate.duration = testcase.duration
        duplicate.reruns = testcase.reruns

    duplicate.result = Result.failed
    return duplicate
