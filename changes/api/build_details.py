from __future__ import absolute_import

from collections import defaultdict
from flask_restful.reqparse import RequestParser
from itertools import groupby
from sqlalchemy.orm import contains_eager, joinedload, subqueryload_all
from typing import List
from uuid import UUID

from changes.api.base import APIView
from changes.api.serializer.models.testcase import TestCaseWithOriginCrumbler
from changes.config import db
from changes.constants import Result, Status
from changes.lib import build_type
from changes.models.build import Build, BuildPriority
from changes.models.buildseen import BuildSeen
from changes.models.event import Event
from changes.models.failurereason import FailureReason
from changes.models.job import Job
from changes.models.jobstep import JobStep
from changes.models.source import Source
from changes.models.test import TestCase
from changes.models.user import User

from changes.utils.originfinder import find_failure_origins


def find_changed_tests(current_build, previous_build, limit=25):
    current_job_ids = [j.id.hex for j in current_build.jobs]
    previous_job_ids = [j.id.hex for j in previous_build.jobs]

    if not (current_job_ids and previous_job_ids):
        return []

    current_job_clause = ', '.join(
        ':c_job_id_%s' % i for i in range(len(current_job_ids))
    )
    previous_job_clause = ', '.join(
        ':p_job_id_%s' % i for i in range(len(previous_job_ids))
    )

    params = {}
    for idx, job_id in enumerate(current_job_ids):
        params['c_job_id_%s' % idx] = job_id
    for idx, job_id in enumerate(previous_job_ids):
        params['p_job_id_%s' % idx] = job_id

    # find all tests that have appeared in one job but not the other
    # we have to build this query up manually as sqlalchemy doesnt support
    # the FULL OUTER JOIN clause
    query = """
        SELECT c.id AS c_id,
               p.id AS p_id
        FROM (
            SELECT label_sha, id
            FROM test
            WHERE job_id IN (%(current_job_clause)s)
        ) as c
        FULL OUTER JOIN (
            SELECT label_sha, id
            FROM test
            WHERE job_id IN (%(previous_job_clause)s)
        ) as p
        ON c.label_sha = p.label_sha
        WHERE (c.id IS NULL OR p.id IS NULL)
    """ % {
        'current_job_clause': current_job_clause,
        'previous_job_clause': previous_job_clause
    }

    total = db.session.query(
        'count'
    ).from_statement(
        'SELECT COUNT(*) FROM (%s) as a' % (query,)
    ).params(**params).scalar()

    if not total:
        return {
            'total': 0,
            'changes': [],
        }

    results = db.session.query(
        'c_id', 'p_id'
    ).from_statement(
        '%s LIMIT %d' % (query, limit)
    ).params(**params)

    all_test_ids = set()
    for c_id, p_id in results:
        if c_id:
            all_test_ids.add(c_id)
        else:
            all_test_ids.add(p_id)

    test_map = dict(
        (t.id, t) for t in TestCase.query.filter(
            TestCase.id.in_(all_test_ids),
        ).options(
            joinedload('job', innerjoin=True),
        )
    )

    diff = []
    for c_id, p_id in results:
        if p_id:
            diff.append(('-', test_map[UUID(p_id)]))
        else:
            diff.append(('+', test_map[UUID(c_id)]))

    return {
        'total': total,
        'changes': sorted(diff, key=lambda x: (x[1].package, x[1].name)),
    }


def get_failure_reasons(build):
    from changes.buildfailures import registry

    rows = FailureReason.query.join(
        JobStep, JobStep.id == FailureReason.step_id,
    ).filter(
        FailureReason.build_id == build.id,
        JobStep.replacement_id.is_(None),
    )

    failure_reasons = []
    for row in rows:
        failure_reasons.append({
            'id': row.reason,
            'reason': registry[row.reason].get_html_label(build),
            'step_id': row.step_id,
            'job_id': row.job_id,
            'data': dict(row.data or {}),
        })

    return failure_reasons


def get_parents_last_builds(build):
    # type: (Build) -> List[Build]
    # A patch have only one parent, while a revision can have more.
    if build.source.patch:
        parents = [build.source.patch.parent_revision_sha]
    elif build.source.revision:
        parents = build.source.revision.parents

    if parents:
        parent_builds = list(Build.query.filter(
            Build.project == build.project,
            Build.status == Status.finished,
            Build.id != build.id,
        ).join(
            Source, Build.source_id == Source.id,
        ).options(
            contains_eager('source').joinedload('revision'),
        ).filter(
            Source.revision_sha.in_(parents),
            *build_type.get_any_commit_build_filters()
        ).order_by(Build.date_created.desc()))
        if parent_builds:
            # This returns a list with the last build of each revision.
            return [
                list(builds)[0]
                for sha, builds in groupby(
                    parent_builds,
                    lambda rev: rev.source.revision_sha
                )
            ]
    return []


class BuildDetailsAPIView(APIView):
    post_parser = RequestParser()
    post_parser.add_argument('priority', choices=BuildPriority._member_names_)

    def get(self, build_id):
        build = Build.query.options(
            joinedload('project', innerjoin=True),
            joinedload('author'),
            joinedload('source').joinedload('revision'),
            subqueryload_all('stats'),
        ).get(build_id)
        if build is None:
            return '', 404

        try:
            most_recent_run = Build.query.filter(
                Build.project == build.project,
                Build.date_created < build.date_created,
                Build.status == Status.finished,
                Build.id != build.id,
            ).join(
                Source, Build.source_id == Source.id,
            ).filter(
                *build_type.get_any_commit_build_filters()
            ).options(
                contains_eager('source').joinedload('revision'),
                joinedload('author'),
            ).order_by(Build.date_created.desc())[0]
        except IndexError:
            most_recent_run = None

        jobs = list(Job.query.filter(
            Job.build_id == build.id,
        ))

        # identify failures
        if not jobs:
            # If we have no jobs, the query to find failures becomes very expensive due to `in_([])` being
            # handled poorly, but since we know the result, we can just set it.
            test_failures = []
            num_test_failures = 0
        else:
            test_failures = TestCase.query.options(
                joinedload('job', innerjoin=True),
            ).filter(
                TestCase.job_id.in_([j.id for j in jobs]),
                TestCase.result == Result.failed,
            ).order_by(TestCase.name.asc())
            num_test_failures = test_failures.count()
            test_failures = test_failures[:25]

        failures_by_job = defaultdict(list)
        for failure in test_failures:
            failures_by_job[failure.job].append(failure)

        failure_origins = find_failure_origins(
            build, test_failures)
        for test_failure in test_failures:
            test_failure.origin = failure_origins.get(test_failure)

        # identify added/removed tests
        if most_recent_run and build.status == Status.finished:
            changed_tests = find_changed_tests(build, most_recent_run)
        else:
            changed_tests = []

        seen_by = list(User.query.join(
            BuildSeen, BuildSeen.user_id == User.id,
        ).filter(
            BuildSeen.build_id == build.id,
        ))

        extended_serializers = {
            TestCase: TestCaseWithOriginCrumbler(),
        }

        event_list = list(Event.query.filter(
            Event.item_id == build.id,
        ).order_by(Event.date_created.desc()))

        context = self.serialize(build)
        context.update({
            'jobs': jobs,
            'seenBy': seen_by,
            'events': event_list,
            'failures': get_failure_reasons(build),
            'testFailures': {
                'total': num_test_failures,
                'tests': self.serialize(test_failures, extended_serializers),
            },
            'testChanges': self.serialize(changed_tests, extended_serializers),
            'parents': self.serialize(get_parents_last_builds(build)),
        })

        return self.respond(context)

    def post(self, build_id):
        build = Build.query.options(
            joinedload('project', innerjoin=True),
            joinedload('author'),
            joinedload('source').joinedload('revision'),
        ).get(build_id)
        if build is None:
            return '', 404

        args = self.post_parser.parse_args()
        if args.priority is not None:
            build.priority = BuildPriority[args.priority]

        db.session.add(build)

        context = self.serialize(build)

        return self.respond(context, serialize=False)
