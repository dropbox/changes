from __future__ import absolute_import, division

import re

from collections import defaultdict
from datetime import datetime
from hashlib import sha1

from changes.config import db
from changes.constants import Result
from changes.db.utils import get_or_create
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

    @property
    def id(self):
        if self.package:
            return '%s.%s' % (self.package, self.name)
        return self.name

    @property
    def sep(self):
        name = (self.package or self.name)
        # handle the case where it might begin with some special character
        if not re.match(r'^[a-zA-Z0-9]', name):
            return '/'
        elif '/' in name:
            return '/'
        return '.'

    @property
    def name_sha(self):
        return TestCase.calculate_name_sha(self.package, self.name)


class TestResultManager(object):
    def __init__(self, build):
        self.build = build

    def regroup_tests(self, test_list):
        grouped = defaultdict(list)

        for test in test_list:
            sep = test.sep
            parts = test.id.split(sep)

            key = []
            for part in parts[:-1]:
                key.append(part)
                grouped[(sep.join(key), sep)].append(test)

        return sorted(grouped.iteritems(), key=lambda x: x[0])

    def count_leaves_with_tests(self, test_list):
        # test.name: set(leaves)
        leaves = defaultdict(set)
        for test in test_list:
            t_id, t_sep = test.id, test.sep

            leaves[t_id].add(t_id)
            parent = t_id.rsplit(t_sep, 1)[0]
            leaves[parent].add(t_id)

            while len(leaves[parent]) > 1 and t_sep in parent:
                parent = parent.rsplit(t_sep, 1)[0]
                leaves[parent].add(parent)

        return dict((k, len(v)) for k, v in leaves.iteritems())

    def find_parent(self, name, sep, groups_by_id):
        if sep not in name:
            return None

        key = name.rsplit(sep, 1)[:-1]
        while key:
            path = sep.join(key)
            if path in groups_by_id:
                return groups_by_id[path]
            key.pop()
        return None

    def create_test_leaf(self, test, parent, testcase):
        build = self.build
        project = build.project
        name_sha = test.name_sha

        group = TestGroup(
            build=build,
            name_sha=name_sha,
            name=test.id,
            suite=test.suite,
            project=project,
            duration=test.duration,
            result=test.result,
            num_failed=1 if test.result == Result.failed else 0,
            num_tests=1,
            num_leaves=0,
            parent=parent,
        )
        db.session.add(group)

        group.testcases.append(testcase)

        return group

    def create_aggregate_test_leaf(self, test, parent):
        build = self.build
        project = build.project
        name_sha = test.name_sha

        agg, created = get_or_create(AggregateTestGroup, where={
            'project': project,
            'name_sha': name_sha,
            'suite_id': None,  # TODO
        }, defaults={
            'name': test.id,
            'parent': parent,
            'first_build_id': build.id,
            'last_build_id': build.id,
        })
        if not created:
            db.session.query(AggregateTestGroup).filter(
                AggregateTestGroup.id == agg.id,
            ).update({
                AggregateTestGroup.last_build_id: build.id,
            }, synchronize_session=False)

        return agg

    def save(self, test_list):
        build = self.build
        project = build.project
        groups_by_id = {}
        tests_by_id = {}
        agg_groups_by_id = {}

        # Eliminate useless parents (parents which only have a single child)
        leaf_counts = self.count_leaves_with_tests(test_list)

        # collect all test groups
        grouped_tests = self.regroup_tests(test_list)
        grouped_tests = [
            (k, t)
            for k, t in grouped_tests
            if leaf_counts.get(k[0], 0) >= 1
        ]

        # create all test cases
        for test in test_list:
            testcase = TestCase(
                build=build,
                name_sha=test.name_sha,
                project=project,
                suite=test.suite,
                name=test.name,
                package=test.package,
                duration=test.duration,
                message=test.message,
                result=test.result,
                date_created=test.date_created,
            )
            db.session.add(testcase)

            tests_by_id[test.id] = testcase

        # Create branches
        for (name, sep), _ in grouped_tests:
            parent = self.find_parent(name, sep, groups_by_id)

            group = TestGroup(
                build=build,
                name_sha=sha1(name).hexdigest(),
                suite=test.suite,
                name=name,
                project=project,
                num_leaves=leaf_counts.get(name),
                parent=parent,
            )
            db.session.add(group)

            groups_by_id[name] = group

            agg, created = get_or_create(AggregateTestGroup, where={
                'project': project,
                'name_sha': group.name_sha,
                'suite_id': None,  # TODO
            }, defaults={
                'name': name,
                'parent': self.find_parent(name, sep, agg_groups_by_id),
                'first_build_id': build.id,
                'last_build_id': build.id,
            })

            if not created:
                db.session.query(AggregateTestGroup).filter(
                    AggregateTestGroup.id == agg.id,
                ).update({
                    AggregateTestGroup.last_build_id: build.id,
                }, synchronize_session=False)

            agg_groups_by_id[name] = agg

        for (name, sep), tests in reversed(grouped_tests):
            branch = groups_by_id[name]
            agg_branch = agg_groups_by_id[name]

            g_duration = 0
            g_failed = 0
            g_total = 0

            # Create any leaves which do not exist yet
            for test in tests:
                testcase = tests_by_id[test.id]

                if test.id not in groups_by_id:
                    leaf = self.create_test_leaf(test, branch, testcase)

                    groups_by_id[leaf.name] = leaf

                if test.id not in agg_groups_by_id:
                    leaf = self.create_aggregate_test_leaf(test, agg_branch)

                    agg_groups_by_id[leaf.name] = leaf

                g_duration += testcase.duration
                g_total += 1
                if testcase.result == Result.failed:
                    g_failed += 1

                if branch.result:
                    branch.result = max(branch.result, testcase.result)
                elif testcase.result:
                    branch.result = testcase.result
                else:
                    branch.result = Result.unknown

            branch.duration = g_duration
            branch.num_failed = g_failed
            branch.num_tests = g_total

            db.session.add(branch)

        db.session.commit()
