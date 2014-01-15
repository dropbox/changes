from __future__ import absolute_import, division

from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy.orm import aliased
from sqlalchemy.sql import func

from changes.config import db
from changes.constants import Status, Result
from changes.models import Build, TestGroup, Source
from changes.utils.http import build_uri


SLOW_TEST_THRESHOLD = 3000  # ms

ONE_DAY = 60 * 60 * 24


class BuildReport(object):
    def __init__(self, projects):
        self.projects = set(projects)

    def generate(self, end_period=None, days=7):
        if end_period is None:
            end_period = datetime.utcnow()

        days_delta = timedelta(days=days)
        start_period = end_period - days_delta

        current_results = self.get_project_stats(
            start_period, end_period)
        previous_results = self.get_project_stats(
            start_period - days_delta, start_period)

        for project, stats in current_results.iteritems():
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

            stats['avg_duration'] = stats['avg_duration']

            stats['percent_change'] = green_change
            stats['duration_change'] = duration_change

        projects_by_green_builds = sorted(
            current_results.items(), key=lambda x: (
                -abs(x[1]['green_percent'] or 0), -(x[1]['percent_change'] or 0),
                x[0].name,
            ))

        projects_by_build_time = sorted(
            current_results.items(), key=lambda x: (
                -abs(x[1]['avg_duration'] or 0), (x[1]['duration_change'] or 0),
                x[0].name,
            ))

        slow_tests = self.get_slow_tests(start_period, end_period)
        # flakey_tests = self.get_frequent_failures(start_period, end_period)
        flakey_tests = []

        title = 'Build Report ({0} through {1})'.format(
            start_period.strftime('%b %d, %Y'),
            end_period.strftime('%b %d, %Y'),
        )

        return {
            'title': title,
            'period': [start_period, end_period],
            'projects_by_build_time': projects_by_build_time,
            'projects_by_green_builds': projects_by_green_builds,
            'tests': {
                'slow_list': slow_tests,
                'flakey_list': flakey_tests,
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
                stats['green_percent'] = int(stats['green_builds'] / stats['total_builds'] * 100)
            else:
                stats['green_percent'] = None

        return project_results

    def get_slow_tests(self, start_period, end_period):
        slow_tests = []
        for project in self.projects:
            slow_tests.extend(self.get_slow_tests_for_project(
                project, start_period, end_period))
        slow_tests.sort(key=lambda x: x['duration_raw'], reverse=True)
        return slow_tests[:10]

    def get_slow_tests_for_project(self, project, start_period, end_period):
        parent_alias = aliased(TestGroup, name='testparent')

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
            TestGroup.name, parent_alias.name, TestGroup.duration,
        ).outerjoin(
            parent_alias, parent_alias.id == TestGroup.parent_id,
        ).filter(
            TestGroup.job_id.in_(j.id for j in job_list),
            TestGroup.num_leaves == 0,
            TestGroup.result == Result.passed,
            TestGroup.date_created > start_period,
            TestGroup.date_created <= end_period,
        ).group_by(
            TestGroup.name, parent_alias.name, TestGroup.duration,
        ).order_by(TestGroup.duration.desc())

        slow_list = []
        for name, parent_name, duration in queryset[:10]:
            if parent_name:
                name = name[len(parent_name) + 1:]

            slow_list.append({
                'project': project,
                'name': name,
                'package': parent_name,
                'duration': '%.2f s' % (duration / 1000.0,),
                'duration_raw': duration,
                # 'link': build_uri('/projects/{0}/tests/{1}/'.format(
                #     project.slug, agg_id.hex)),
            })

        return slow_list

    def get_frequent_failures(self, start_period, end_period):
        projects_by_id = dict((p.id, p) for p in self.projects)
        project_ids = projects_by_id.keys()

        parent_alias = aliased(TestGroup, name='testparent')

        queryset = db.session.query(
            TestGroup.name,
            parent_alias.name,
            TestGroup.project_id,
            TestGroup.result,
            func.count(TestGroup.id).label('num'),
        ).outerjoin(
            parent_alias, parent_alias.id == TestGroup.parent_id,
        ).filter(
            TestGroup.project_id.in_(project_ids),
            TestGroup.num_leaves == 0,
            TestGroup.result.in_([Result.passed, Result.failed]),
            TestGroup.date_created > start_period,
            TestGroup.date_created <= end_period,
        ).group_by(
            TestGroup.name,
            parent_alias.name,
            TestGroup.project_id,
            TestGroup.result,
        )

        test_results = defaultdict(lambda: {
            'passed': 0,
            'failed': 0,
        })
        for name, parent_name, project_id, result, count in queryset:
            test_results[(name, parent_name, project_id)][result.name] += count

        if not test_results:
            return []

        tests_with_pct = []
        for test_key, counts in test_results.iteritems():
            total = counts['passed'] + counts['failed']
            if counts['failed'] == 0:
                continue
            # exclude tests which haven't been seen frequently
            elif total < 5:
                continue
            else:
                pct = counts['failed'] / total * 100
            # if the test has failed 100% of the time, it's not flakey
            if pct == 100:
                continue
            tests_with_pct.append((test_key, pct, total, counts['failed']))
        tests_with_pct.sort(key=lambda x: x[1], reverse=True)

        flakiest_tests = tests_with_pct[:10]

        if not flakiest_tests:
            return []

        results = []
        for test_key, pct, total, fail_count in flakiest_tests:
            (name, parent_name, project_id) = test_key

            if parent_name:
                name = name[len(parent_name) + 1:]

            # project = projects_by_id[project_id]

            results.append({
                'name': name,
                'package': parent_name,
                'fail_pct': int(pct),
                'fail_count': fail_count,
                'total_count': total,
                # 'link': build_uri('/projects/{0}/tests/{1}/'.format(
                #     project.slug, agg.id.hex)),
            })

        return results

    def _date_to_key(self, dt):
        return int(dt.replace(
            minute=0, hour=0, second=0, microsecond=0
        ).strftime('%s'))
