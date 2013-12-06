from __future__ import absolute_import, division

from datetime import datetime
from hashlib import sha1

from changes.config import db
from changes.constants import Result
from changes.db.utils import get_or_create, create_or_get
from changes.models.aggregatetest import AggregateTestGroup
from changes.models.test import TestGroup, TestCase


class TestResult(object):
    """
    A helper class which ensures that TestGroup and TestSuite instances are
    managed correctly when TestCase's are created.
    """
    def __init__(self, build, name, message=None, package=None,
                 result=None, duration=None, date_created=None, suite=None):

        self.build = build
        self.name = name
        self.package = package
        self.message = message
        self.result = result or Result.unknown
        self.duration = duration  # ms
        self.date_created = date_created or datetime.utcnow()
        self.suite = suite

    def _get_or_create_test_groups(self):
        # TODO(dcramer): this doesnt handle concurrency
        # TODO(dcramer): implement subtrees
        # https://github.com/disqus/zumanji/blob/master/src/zumanji/importer.py#L217

        build = self.build
        project = self.build.project

        labels = []
        if self.package:
            labels.extend([
                self.package,
                '%s.%s' % (self.package, self.name),
            ])
        else:
            try:
                package = self.name.rsplit('.', 1)[0]
            except IndexError:
                labels.append(self.name)
            else:
                labels.extend([
                    package,
                    self.name,
                ])

        groups = []
        parent_id, agg_parent_id = None, None
        for idx, label in enumerate(labels):
            group, _ = get_or_create(TestGroup, where={
                'build': build,
                'name_sha': sha1(label).hexdigest(),
            }, defaults={
                'name': label,
                'project': project,
                'num_leaves': len(labels) - 1 - idx,
                'parent_id': parent_id,
            })
            parent_id = group.id

            # TODO(dcramer): last_build/first_build probably make less sense
            # if we are only looking for a single revision-based build
            # (e.g. on the master branch)
            agg, created = create_or_get(AggregateTestGroup, where={
                'project': project,
                'name_sha': group.name_sha,
            }, values={
                'name': label,
                'parent_id': agg_parent_id,
                'first_build_id': build.id,
                'last_build_id': build.id,
            })
            agg_parent_id = agg.id

            if not created:
                db.session.query(AggregateTestGroup).filter(
                    AggregateTestGroup.id == agg.id,
                ).update({
                    AggregateTestGroup.last_build_id: build.id,
                }, synchronize_session=False)

            groups.append(group)

        return groups

    def save(self):
        name_sha = TestCase.calculate_name_sha(self.package, self.name)

        test, created = create_or_get(TestCase, where={
            'build': self.build,
            'suite_id': self.suite.id,
            'name_sha': name_sha,
        }, values={
            'project': self.build.project,
            'name': self.name,
            'package': self.package,
            'duration': self.duration,
            'message': self.message,
            'result': self.result,
            'date_created': self.date_created,
        })
        if not created:
            return

        db.session.commit()

        groups = self._get_or_create_test_groups()
        for group in groups:
            if group.result:
                group.result = max(group.result, test.result)
            elif test.result:
                group.result = test.result
            else:
                group.result = Result.unknown

            group.testcases.append(test)

            db.session.query(TestGroup).filter(
                TestGroup.id == group.id,
            ).update({
                TestGroup.num_tests: TestGroup.num_tests + 1,
                TestGroup.duration: TestGroup.duration + test.duration,
                TestGroup.num_failed: TestGroup.num_failed + int(test.result == Result.failed),
                TestGroup.result: group.result,
            })

            db.session.commit()

        return test
