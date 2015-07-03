from __future__ import absolute_import, division

import logging
import re

from collections import defaultdict
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import func

from changes.config import db
from changes.constants import Result
from changes.db.utils import create_or_update, try_create
from changes.models import FailureReason, ItemStat, TestCase, TestArtifact

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
        # agg_groups_by_id = {}

        test_list = _detect_duplicate_tests(test_list)

        # create all test cases
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
            db.session.add(testcase)

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
        except IntegrityError:
            db.session.rollback()
            logger.exception('Duplicate test name; (step={})'.format(step.id.hex))
            try_create(FailureReason, {
                'step_id': step.id,
                'job_id': step.job_id,
                'build_id': step.job.build_id,
                'project_id': step.project_id,
                'reason': 'duplicate_test_name'
            })
            db.session.commit()

        try:
            self._record_test_counts(test_list)
            self._record_test_failures(test_list)
            self._record_test_duration(test_list)
            self._record_test_rerun_counts(test_list)
        except Exception:
            logger.exception('Failed to record aggregate test statistics')

    def _record_test_counts(self, test_list):
        create_or_update(ItemStat, where={
            'item_id': self.step.id,
            'name': 'test_count',
        }, values={
            'value': db.session.query(func.count(TestCase.id)).filter(
                TestCase.step_id == self.step.id,
            ).as_scalar(),
        })
        db.session.commit()

    def _record_test_failures(self, test_list):
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

    def _record_test_duration(self, test_list):
        create_or_update(ItemStat, where={
            'item_id': self.step.id,
            'name': 'test_duration',
        }, values={
            'value': db.session.query(func.coalesce(func.sum(TestCase.duration), 0)).filter(
                TestCase.step_id == self.step.id,
            ).as_scalar(),
        })

    def _record_test_rerun_counts(self, test_list):
        create_or_update(ItemStat, where={
            'item_id': self.step.id,
            'name': 'test_rerun_count',
        }, values={
            'value': db.session.query(func.count(TestCase.id)).filter(
                TestCase.step_id == self.step.id,
                TestCase.reruns > 0,
            ).as_scalar(),
        })


def _detect_duplicate_tests(test_list):
    """Return a new `test_list` where any duplicates are marked as failures.

    The new list will be in the same order as the original, but with the
    second and subsequent instances of a given test removed.

    """
    groups = defaultdict(list)
    for test in test_list:
        groups[test.name_sha].append(test)
    new_list = []
    for test in test_list:
        group = groups.pop(test.name_sha, None)
        if group is None:
            pass
        elif len(group) == 1:
            new_list.append(test)
        elif len(group) > 1:
            result = TestResult(
                step=test.step,
                name=test._name,
                package=test._package,
                message='Duplicate test. Ran {} times in steps {}.'.format(
                    len(group), ', '.join(str(t.step.id) for t in group)),
                result=Result.failed,
                duration=sum((t.duration or 0) for t in group),
                reruns=sum((t.reruns or 0) for t in group),
                artifacts=sum([(t.artifacts or []) for t in group], []),
                )
            new_list.append(result)

    return new_list
