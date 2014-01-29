from datetime import datetime, timedelta
from flask import request
from sqlalchemy import distinct, and_
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func, literal

from changes.api.base import APIView
from changes.config import db
from changes.constants import Status, Result
from changes.models import TestGroup, Project, Build, Job, Source
from changes.reports.build import SLOW_TEST_THRESHOLD


def parse_date(value):
    from dateutil.parser import parse
    return parse(value)


def get_build_history(project, end_period, days=90):
    def date_to_key(dt):
        return int(dt.replace(
            minute=0, hour=0, second=0, microsecond=0
        ).strftime('%s'))

    query = db.session.query(
        Job.result,
        func.count('*').label('num'),
        func.date_trunc(literal('day'), Job.date_created).label('date')
    ).filter(
        Job.project_id == project.id,
        Job.date_created >= end_period - timedelta(days=days),
        Job.date_created < end_period,
        Job.status == Status.finished,
        Source.revision_sha != None,  # NOQA
        Source.patch_id == None,
    ).group_by(Job.result, 'date').order_by('date asc')

    # group results by day
    results = {}
    for n in xrange(days):
        results[date_to_key(end_period - timedelta(days=n))] = {
            'counts': {
                'passed': 0,
                'failed': 0,
                'aborted': 0,
                'unknown': 0,
            },
            'numBuilds': 0,
        }

    for result, num, date in query:
        this = results[date_to_key(date)]
        this['counts'][result.name] += num
        this['numBuilds'] += num

    return results


def get_stats_for_period(project, start_period, end_period):
    num_passes = Job.query.filter(
        Job.project_id == project.id,
        Job.status == Status.finished,
        Job.result == Result.passed,
        Job.date_created >= start_period,
        Job.date_created < end_period,
        Source.revision_sha != None,  # NOQA
    ).count()
    num_failures = Job.query.filter(
        Job.project_id == project.id,
        Job.status == Status.finished,
        Job.result == Result.failed,
        Job.date_created >= start_period,
        Job.date_created < end_period,
        Source.revision_sha != None,  # NOQA
    ).count()
    num_builds = Job.query.filter(
        Job.project_id == project.id,
        Job.status == Status.finished,
        Job.date_created >= start_period,
        Job.date_created < end_period,
        Source.revision_sha != None,  # NOQA
    ).count()

    num_authors = db.session.query(
        func.count(distinct(Build.author_id))
    ).filter(
        Build.project_id == project.id,
        Build.status == Status.finished,
        Build.date_created >= start_period,
        Build.date_created < end_period,
        Source.revision_sha != None,  # NOQA
    ).scalar()

    avg_build_time = db.session.query(
        func.avg(Job.duration).label('avg_build_time'),
    ).filter(
        Job.project_id == project.id,
        Job.status == Status.finished,
        Job.result == Result.passed,
        Job.duration > 0,
        Job.date_created >= start_period,
        Job.date_created < end_period,
        Source.revision_sha != None,  # NOQA
    ).scalar()
    if avg_build_time is not None:
        avg_build_time = float(avg_build_time)

    bugs_caught_with_patches = db.session.query(
        Job
    ).filter(
        Job.project_id == project.id,
        Job.status == Status.finished,
        Job.result == Result.failed,
        Job.date_created >= start_period,
        Job.date_created < end_period,
        Source.patch_id != None,  # NOQA
    ).count()

    return {
        'period': [start_period, end_period],
        'numFailed': num_failures,
        'numPassed': num_passes,
        'numBuilds': num_builds,
        'avgBuildTime': avg_build_time,
        'numAuthors': num_authors,
        'bugsCaughtFromPatches': bugs_caught_with_patches,
    }


class ProjectStatsIndexAPIView(APIView):
    def _get_project(self, project_id):
        project = Project.query.options(
            joinedload(Project.repository, innerjoin=True),
        ).filter_by(slug=project_id).first()
        if project is None:
            project = Project.query.options(
                joinedload(Project.repository, innerjoin=True),
            ).get(project_id)
        return project

    def get(self, project_id):
        project = self._get_project(project_id)

        period_length = int(request.args.get('days') or 7)

        end_period = request.args.get('end')
        if end_period:
            end_period = parse_date(end_period)
        else:
            end_period = datetime.now()

        start_period = request.args.get('start')
        if start_period:
            start_period = parse_date(start_period)
        else:
            start_period = end_period - timedelta(days=period_length)

        current_build = Job.query.options(
            joinedload(Job.project, innerjoin=True),
        ).filter(
            Source.revision_sha != None,  # NOQA
            Source.patch_id == None,
            Job.project == project,
            Job.status == Status.finished,
        ).order_by(
            Job.date_created.desc(),
        ).first()

        # TODO(dcramer): if this is useful, we should denormalize testgroups
        # identify all names which were first seen in the last week
        # and have exceeded the threshold (ever)
        stmt = db.session.query(
            TestGroup.name_sha
        ).filter(
            TestGroup.project_id == project.id,
            TestGroup.num_leaves == 0,
            TestGroup.duration > SLOW_TEST_THRESHOLD,
        ).group_by(TestGroup.name_sha).having(
            and_(
                func.min(TestGroup.date_created) >= start_period,
                func.min(TestGroup.date_created) < end_period,
            )
        ).subquery('t')

        # find current build tests which are still over threshold and match
        # our names
        new_slow_tests = db.session.query(TestGroup).filter(
            TestGroup.job_id == current_build.id,
            TestGroup.duration > SLOW_TEST_THRESHOLD,
            TestGroup.name_sha.in_(stmt),
        ).order_by(TestGroup.duration.desc()).limit(100)

        new_slow_tests = list(new_slow_tests)

        previous_end_period = start_period
        previous_start_period = previous_end_period - (end_period - start_period)

        current_period = get_stats_for_period(
            project, start_period, end_period)
        previous_period = get_stats_for_period(
            project, previous_start_period, previous_end_period)

        # get summary statistics
        build_stats = current_period
        build_stats['previousPeriod'] = previous_period

        # get trailing 90 days of build statistics
        build_history = get_build_history(project, end_period)

        context = {
            'buildStats': build_stats,
            'buildHistory': build_history,
            'newSlowTestGroups': new_slow_tests,
        }

        return self.respond(context)
