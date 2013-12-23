from __future__ import absolute_import, division

from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy.orm import joinedload, subqueryload
from sqlalchemy.sql import func, and_

from changes.config import db
from changes.constants import Status, Result
from changes.models import Build, AggregateTestGroup, TestGroup
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
        flakey_tests = self.get_frequent_failures(start_period, end_period)

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
        ).filter(
            Build.revision_sha != None,  # NOQA
            Build.patch_id == None,
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
        projects_by_id = dict((p.id, p) for p in self.projects)
        project_ids = projects_by_id.keys()

        queryset = db.session.query(AggregateTestGroup, TestGroup).options(
            joinedload(AggregateTestGroup.last_build),
            subqueryload(TestGroup.parent),
        ).join(
            TestGroup, and_(
                TestGroup.build_id == AggregateTestGroup.last_build_id,
                TestGroup.name_sha == AggregateTestGroup.name_sha,
            )
        ).join(
            AggregateTestGroup.last_build,
        ).filter(
            AggregateTestGroup.project_id.in_(project_ids),
            TestGroup.num_leaves == 0,
            Build.date_created > start_period,
            Build.date_created <= end_period,
        ).order_by(TestGroup.duration.desc())

        slow_list = []
        for agg, group in queryset[:10]:
            package, name = group.name.rsplit('.', 1)
            if group.parent:
                package = group.parent.name
                name = group.name[len(group.parent.name) + 1:]
            else:
                package = None
                name = group.name

            project = projects_by_id[group.project_id]

            slow_list.append({
                'project': project,
                'name': name,
                'package': package,
                'duration': '%.2f s' % (group.duration / 1000.0,),
                'link': build_uri('/projects/{0}/tests/{1}/'.format(
                    project.slug, agg.id.hex)),
            })

        return slow_list

    def get_frequent_failures(self, start_period, end_period):
        projects_by_id = dict((p.id, p) for p in self.projects)
        project_ids = projects_by_id.keys()

        queryset = db.session.query(
            AggregateTestGroup.id,
            TestGroup.result,
            func.count(TestGroup.id).label('num'),
        ).join(
            TestGroup, and_(
                TestGroup.project_id == AggregateTestGroup.project_id,
                TestGroup.name_sha == AggregateTestGroup.name_sha,
            )
        ).join(
            TestGroup.build,
        ).filter(
            AggregateTestGroup.project_id.in_(project_ids),
            TestGroup.num_leaves == 0,
            TestGroup.result.in_([Result.passed, Result.failed]),
            Build.date_created > start_period,
            Build.date_created <= end_period,
        ).group_by(
            AggregateTestGroup.id,
            TestGroup.result,
        )

        test_results = defaultdict(lambda: {
            'passed': 0,
            'failed': 0,
        })
        for agg_id, result, count in queryset:
            test_results[agg_id][result.name] += count

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

        aggregates = dict(
            (a.id, a)
            for a in AggregateTestGroup.query.options(
                subqueryload(AggregateTestGroup.parent),
            ).filter(
                AggregateTestGroup.id.in_([x[0] for x in flakiest_tests])
            )
        )

        results = []
        for test_key, pct, total, fail_count in flakiest_tests:
            agg = aggregates[test_key]

            package, name = agg.name.rsplit('.', 1)
            if agg.parent:
                package = agg.parent.name
                name = agg.name[len(agg.parent.name) + 1:]
            else:
                package = None
                name = agg.name

            project = projects_by_id[agg.project_id]

            results.append({
                'name': name,
                'package': package,
                'fail_pct': int(pct),
                'fail_count': fail_count,
                'total_count': total,
                'link': build_uri('/projects/{0}/tests/{1}/'.format(
                    project.slug, agg.id.hex)),
            })

        return results

    def _date_to_key(self, dt):
        return int(dt.replace(
            minute=0, hour=0, second=0, microsecond=0
        ).strftime('%s'))
