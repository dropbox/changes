from __future__ import absolute_import, division

import logging
import re

from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import func

from changes.config import db
from changes.constants import Result
from changes.db.utils import create_or_update
from changes.models import FailureReason, ItemStat, TestArtifact
from changes.models.test import TestCase

logger = logging.getLogger('changes.testresult')


class TestResult(object):
    """
    A helper class which ensures that TestSuite instances are
    managed correctly when TestCase's are created.
    """
    def __init__(self, step, name, message=None, package=None,
                 result=None, duration=None, date_created=None,
                 reruns=None, artifacts=None, owner=None):
        self.step = step
        self._name = name
        self._package = package
        self.message = message
        self.result = result or Result.unknown
        self.duration = duration  # ms
        self.date_created = date_created or datetime.utcnow()
        self.reruns = reruns or 0
        self.artifacts = artifacts
        self.owner = owner

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

        # For tracking the name of any test we see with a bad
        # duration, typically the first one if we see multiple.
        bad_duration_test_name = None
        bad_duration_value = None

        for test in test_list:
            duration = test.duration
            # Maximum value for the Integer column type
            if duration is not None and (duration > 2147483647 or duration < 0):
                # If it is very large (>~25 days) or negative set it to 0
                # since it is almost certainly wrong, and keeping it or truncating
                # to max will give misleading total values.
                if not bad_duration_test_name:
                    bad_duration_test_name = test.name
                    bad_duration_value = duration
                duration = 0
            testcase = TestCase(
                job=job,
                step=step,
                name_sha=test.name_sha,
                project=project,
                name=test.name,
                duration=duration,
                message=test.message,
                result=test.result,
                date_created=test.date_created,
                reruns=test.reruns,
                owner=test.owner,
            )
            testcase_list.append(testcase)

        if bad_duration_test_name:
            # Include the project slug in the warning so project warnings aren't bucketed together.
            logger.warning("Got bad test duration for " + project.slug + "; %s: %s",
                           bad_duration_test_name, bad_duration_value)

        # Try an optimistic commit of all cases at once.
        for testcase in testcase_list:
            db.session.add(testcase)

        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()

            create_or_update(FailureReason, where={
                'step_id': step.id,
                'reason': 'duplicate_test_name',
            }, values={
                'project_id': step.project_id,
                'build_id': step.job.build_id,
                'job_id': step.job_id,
            })
            db.session.commit()

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


_DUPLICATE_TEST_COMPLAINT = """Error: Duplicate Test

Your test suite is reporting multiple results for this test, but Changes
can only store a single success or failure for each test.

  * If you did not intend to run this test several times, simply repair
    your scripts so that this test is only discovered and invoked once.

  * If you intended to run this test several times and then report a
    single success or failure, then run it inside of a loop yourself,
    aggregate the results, and deliver a single verdict to Changes.

  * If you want to invoke this test several times and have each result
    reported separately, then give each run a unique name.  Many testing
    frameworks will do this automatically, appending a unique suffix
    like "#1" or "[1]", when a test is invoked through a fixture.

Here are the job steps that reported a result for this test:

"""


def _record_duplicate_testcase(duplicate):
    """Find the TestCase that already exists for `duplicate` and update it.

    Because of the unique constraint on TestCase, we cannot record the
    `duplicate`.  Instead, we go back and mark the first instance as
    having failed because of the duplication, but discard all of the
    other data delivered with the `duplicate`.

    """
    original = (
        TestCase.query
        .filter_by(job_id=duplicate.job_id, name_sha=duplicate.name_sha)
        .with_for_update().first()
        )

    prefix = _DUPLICATE_TEST_COMPLAINT
    if (original.message is None) or not original.message.startswith(prefix):
        original.message = '{}{}\n'.format(prefix, original.step.label)
        original.result = Result.failed

    if duplicate.step.label not in original.message:
        original.message += '{}\n'.format(duplicate.step.label)

    return original
