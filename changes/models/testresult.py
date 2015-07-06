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
                    original = _record_duplicate_testcase(testcase)
                    db.session.commit()
                    testcase_list[i] = original  # so artifacts get stored
                    _record_test_failures(original.step)  # so count is right

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
            _record_test_counts(self.step)
            _record_test_failures(self.step)
            _record_test_duration(self.step)
            _record_test_rerun_counts(self.step)
        except Exception:
            db.session.rollback()
            logger.exception('Failed to record aggregate test statistics'
                             ' for step {}'.format(step.id.hex))


def _record_test_counts(step):
    create_or_update(ItemStat, where={
        'item_id': step.id,
        'name': 'test_count',
    }, values={
        'value': db.session.query(func.count(TestCase.id)).filter(
            TestCase.step_id == step.id,
        ).as_scalar(),
    })
    db.session.commit()


def _record_test_failures(step):
    create_or_update(ItemStat, where={
        'item_id': step.id,
        'name': 'test_failures',
    }, values={
        'value': db.session.query(func.count(TestCase.id)).filter(
            TestCase.step_id == step.id,
            TestCase.result == Result.failed,
        ).as_scalar(),
    })
    db.session.commit()


def _record_test_duration(step):
    create_or_update(ItemStat, where={
        'item_id': step.id,
        'name': 'test_duration',
    }, values={
        'value': db.session.query(func.coalesce(func.sum(TestCase.duration), 0)).filter(
            TestCase.step_id == step.id,
        ).as_scalar(),
    })


def _record_test_rerun_counts(step):
    create_or_update(ItemStat, where={
        'item_id': step.id,
        'name': 'test_rerun_count',
    }, values={
        'value': db.session.query(func.count(TestCase.id)).filter(
            TestCase.step_id == step.id,
            TestCase.reruns > 0,
        ).as_scalar(),
    })


def _record_duplicate_testcase(duplicate):
    """Find the TestCase that already exists for `duplicate` and update it.

    Because of the unique constraint on TestCase, we cannot record the
    `duplicate`.  Instead, we go back and mark the first instance as
    having failed because of the duplication, but discard all of the
    other data delivered with the `duplicate`.

    """
    original = TestCase.query.filter_by(
            job_id=duplicate.job_id, name_sha=duplicate.name_sha
        ).with_for_update().first()

    prefix = 'Duplicate test in step'
    if (original.message is None) or not original.message.startswith(prefix):
        original.message = '{} {}'.format(prefix, original.step.label)
        original.result = Result.failed

    if duplicate.step.label not in original.message:
        original.message += ' and {}'.format(duplicate.step.label)

    return original
