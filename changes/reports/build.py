from __future__ import absolute_import, division

from collections import defaultdict
from datetime import datetime, timedelta
from hashlib import sha1
from sqlalchemy.sql import func
from sqlalchemy.orm import subqueryload_all

from changes.config import db
from changes.constants import Status, Result
from changes.models import Build, TestCase, Source
from changes.utils.http import build_uri


SLOW_TEST_THRESHOLD = 3000  # ms

ONE_DAY = 60 * 60 * 24


def percent(value, total):
    if not (value and total):
        return 0
    return int(value / total * 100)


class BuildReport(object):
    def __init__(self, projects):
        self.projects = set(projects)

    def generate(self, end_period=None, days=7):
        if end_period is None:
            end_period = datetime.utcnow()

        days_delta = timedelta(days=days)
        start_period = end_period - days_delta

        # if we're pulling data for a select number of days let's use the
        # previous week as the previous period
        if days < 7:
            previous_end_period = start_period - timedelta(days=7)
        else:
            previous_end_period = start_period
        previous_start_period = previous_end_period - days_delta

        current_results = self.get_project_stats(
            start_period, end_period)
        previous_results = self.get_project_stats(
            previous_start_period, previous_end_period)

        for project, stats in current_results.items():
            # exclude projects that had no builds in this period
            if not stats['total_builds']:
                del current_results[project]
                continue

            previous_stats = previous_results.get(project)
            if not previous_stats:
                green_change = None
                duration_change = None
            elif stats['green_percent'] is None:
                green_change = None
                duration_change = None
            elif previous_stats['green_percent'] is None:
                green_change = None
                duration_change = None
            else:
                green_change = stats['green_percent'] - previous_stats['green_percent']
                duration_change = stats['avg_duration'] - previous_stats['avg_duration']

            if not previous_stats:
                total_change = None
            elif previous_stats['total_builds'] is None:
                total_change = None
            else:
                total_change = stats['total_builds'] - previous_stats['total_builds']

            stats['avg_duration'] = stats['avg_duration']

            stats['total_change'] = total_change
            stats['percent_change'] = green_change
            stats['duration_change'] = duration_change

        projects_by_green_builds = sorted(
            current_results.items(), key=lambda x: (
                abs(x[1]['green_percent'] or 0), -(x[1]['percent_change'] or 0),
                x[0].name,
            ))

        current_failure_stats = self.get_failure_stats(
            start_period, end_period)
        previous_failure_stats = self.get_failure_stats(
            previous_start_period, previous_end_period)
        failure_stats = []
        for stat_name, current_stat_value in current_failure_stats['reasons'].iteritems():
            previous_stat_value = previous_failure_stats['reasons'].get(stat_name, 0)
            failure_stats.append({
                'name': stat_name,
                'current': {
                    'value': current_stat_value,
                    'percent': percent(current_stat_value, current_failure_stats['total'])
                },
                'previous': {
                    'value': previous_stat_value,
                    'percent': percent(previous_stat_value, previous_failure_stats['total'])
                },
            })

        slow_tests = self.get_slow_tests(start_period, end_period)

        title = 'Build Report ({0} through {1})'.format(
            start_period.strftime('%b %d, %Y'),
            end_period.strftime('%b %d, %Y'),
        )
        if len(self.projects) == 1:
            title = '[%s] %s' % (iter(self.projects).next().name, title)

        return {
            'title': title,
            'period': [start_period, end_period],
            'failure_stats': failure_stats,
            'projects_by_green_builds': projects_by_green_builds,
            'tests': {
                'slow_list': slow_tests,
            },
        }

    def get_project_stats(self, start_period, end_period):
        projects_by_id = dict((p.id, p) for p in self.projects)
        project_ids = projects_by_id.keys()

        # fetch overall build statistics per project
        query = db.session.query(
            Build.project_id, Build.result,
            func.count(Build.id).label('num'),
            func.avg(Build.duration).label('duration'),
        ).join(
            Source, Source.id == Build.source_id,
        ).filter(
            Source.patch_id == None,  # NOQA
            Build.project_id.in_(project_ids),
            Build.status == Status.finished,
            Build.result.in_([Result.failed, Result.passed]),
            Build.date_created >= start_period,
            Build.date_created < end_period,
        ).group_by(Build.project_id, Build.result)

        project_results = {}
        for project in self.projects:
            project_results[project] = {
                'total_builds': 0,
                'green_builds': 0,
                'green_percent': None,
                'avg_duration': 0,
                'link': build_uri('/projects/{0}/'.format(project.slug)),
            }

        for project_id, result, num_builds, duration in query:
            if duration is None:
                duration = 0

            project = projects_by_id[project_id]

            if result == Result.passed:
                project_results[project]['avg_duration'] = duration

            project_results[project]['total_builds'] += num_builds
            if result == Result.passed:
                project_results[project]['green_builds'] += num_builds

        for project, stats in project_results.iteritems():
            if stats['total_builds']:
                stats['green_percent'] = percent(stats['green_builds'], stats['total_builds'])
            else:
                stats['green_percent'] = None

        return project_results

    def get_failure_stats(self, start_period, end_period):
        failure_stats = {
            'total': 0,
            'reasons': defaultdict(int),
        }
        for project in self.projects:
            for stat, value in self.get_failure_stats_for_project(
                    project, start_period, end_period).iteritems():
                failure_stats['reasons'][stat] += value

        failure_stats['total'] = Build.query.filter(
            Build.status == Status.finished,
            Build.result == Result.failed,
            Build.date_created >= start_period,
            Build.date_created < end_period,
        ).count()

        return failure_stats

    def get_failure_stats_for_project(self, project, start_period, end_period):
        stats = {
            'Test Failures': 0,
            'Missing Tests': 0,
        }
        # TODO(dcramer): we should embed this logic into the job/build results
        failing_builds = Build.query.filter(
            Build.project_id == project.id,
            Build.status == Status.finished,
            Build.result == Result.failed,
            Build.date_created >= start_period,
            Build.date_created < end_period,
        ).options(
            subqueryload_all('stats'),
        )
        for build in failing_builds:
            build_stats = dict((s.name, s.value) for s in build.stats)
            if build_stats.get('test_failures', 0):
                stats['Test Failures'] += 1
            if build_stats.get('tests_missing', 0):
                stats['Missing Tests'] += 1
        return stats

    def get_slow_tests(self, start_period, end_period):
        slow_tests = []
        for project in self.projects:
            slow_tests.extend(self.get_slow_tests_for_project(
                project, start_period, end_period))
        slow_tests.sort(key=lambda x: x['duration_raw'], reverse=True)
        return slow_tests[:10]

    def get_slow_tests_for_project(self, project, start_period, end_period):
        latest_build = Build.query.filter(
            Build.project == project,
            Build.status == Status.finished,
            Build.result == Result.passed,
            Build.date_created >= start_period,
            Build.date_created < end_period,
        ).order_by(
            Build.date_created.desc(),
        ).limit(1).first()

        if not latest_build:
            return []

        job_list = list(latest_build.jobs)
        if not job_list:
            return []

        queryset = db.session.query(
            TestCase.name, TestCase.duration,
        ).filter(
            TestCase.job_id.in_(j.id for j in job_list),
            TestCase.result == Result.passed,
            TestCase.date_created > start_period,
            TestCase.date_created <= end_period,
        ).group_by(
            TestCase.name, TestCase.duration,
        ).order_by(TestCase.duration.desc())

        slow_list = []
        for name, duration in queryset[:10]:
            slow_list.append({
                'project': project,
                'name': name,
                'package': '',  # TODO
                'duration': '%.2f s' % (duration / 1000.0,),
                'duration_raw': duration,
                'link': build_uri('/projects/{0}/tests/{1}/'.format(
                    project.slug, sha1(name).hexdigest())),
            })

        return slow_list

    def _date_to_key(self, dt):
        return int(dt.replace(
            minute=0, hour=0, second=0, microsecond=0
        ).strftime('%s'))
