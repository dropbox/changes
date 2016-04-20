from __future__ import absolute_import, division, unicode_literals

from datetime import datetime, timedelta
from flask.ext.restful import reqparse
from sqlalchemy.sql import func
from sqlalchemy import and_

from changes.api.base import APIView, error
from changes.config import db
from changes.models.flakyteststat import FlakyTestStat
from changes.models.project import Project
from changes.models.test import TestCase


CHART_DATA_LIMIT = 50


class ProjectFlakyTestsAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('date', type=unicode, location='args')

    def get(self, project_id):
        project = Project.get(project_id)
        if not project:
            return error("Project not found", http_code=404)

        args = self.parser.parse_args()
        if args.date:
            try:
                query_date = datetime.strptime(args.date, '%Y-%m-%d').date()
            except:
                return error('Can\'t parse date "%s"' % (args.date))
        else:
            # This `7` is hard-coded to match the code in config.py which kicks
            # off the cron job 7 hours past midnight GMT (which corresponds to
            # midnight PST)
            delta = timedelta(days=2 if datetime.utcnow().hour < 7 else 1)
            query_date = datetime.utcnow().date() - delta

        data = {
            'date': str(query_date),
            'chartData': self.get_chart_data(project_id, query_date),
            'flakyTests': self.get_flaky_tests(project_id, query_date)
        }

        return self.respond(data)

    def get_flaky_tests(self, project_id, query_date):
        subquery = db.session.query(
            FlakyTestStat,
            TestCase
        ).filter(
            FlakyTestStat.project_id == project_id
        ).join(
            TestCase
        )

        flakytests_query = subquery.filter(
            FlakyTestStat.date == query_date
        )

        flaky_map = {}
        for flaky_test, test_run in flakytests_query:
            flaky_map[test_run.name_sha] = {
                'id': test_run.id,
                'job_id': test_run.job_id,
                'build_id': test_run.job.build_id,
                'project_id': test_run.project_id,
                'name': flaky_test.name,
                'short_name': test_run.short_name,
                'package': test_run.package,
                'hash': test_run.name_sha,
                'flaky_runs': flaky_test.flaky_runs,
                'double_reruns': flaky_test.double_reruns,
                'passing_runs': flaky_test.passing_runs,
                'first_run': str(flaky_test.first_run),
                'output': test_run.message,
                'history': []
            }

        if flaky_map:
            history_query = subquery.filter(
                FlakyTestStat.date <= query_date,
                FlakyTestStat.date > (query_date - timedelta(days=CHART_DATA_LIMIT)),
                FlakyTestStat.name.in_([flaky_test['name'] for flaky_test in flaky_map.values()])
            )

            # Create dict with keys in range ]today-CHART_DATA_LIMIT, today]
            calendar = [query_date - timedelta(days=delta) for delta in range(0, CHART_DATA_LIMIT)]
            history = {}
            for day in calendar:
                history[str(day)] = {}

            # Insert stats in the dict
            for flaky_test, test_run in history_query:
                history[str(flaky_test.date)][test_run.name_sha] = {
                    'date': str(flaky_test.date),
                    'flaky_runs': flaky_test.flaky_runs,
                    'double_reruns': flaky_test.double_reruns,
                    'passing_runs': flaky_test.passing_runs,
                    'test_existed': True
                }

            # For each test, generate its history array from global history dict
            for day in reversed(sorted(history)):
                for sha in flaky_map:
                    test_existed = flaky_map[sha]['first_run'] and day > flaky_map[sha]['first_run']
                    default_data = {
                        'date': day,
                        'flaky_runs': 0,
                        'double_reruns': 0,
                        'passing_runs': 0,
                        'test_existed': test_existed
                    }
                    flaky_map[sha]['history'].append(history[day].get(sha, default_data))

        flaky_tests = [flaky_map[sha] for sha in flaky_map]
        return sorted(
            flaky_tests,
            key=lambda x: (x['double_reruns'], x['flaky_runs']),
            reverse=True
        )

    def get_chart_data(self, project_id, query_date):
        calendar = db.session.query(
            func.generate_series(
                query_date - timedelta(days=CHART_DATA_LIMIT - 1),
                query_date,
                timedelta(days=1)
            ).label('day')
        ).subquery()

        historical_data = db.session.query(
            calendar.c.day,
            func.coalesce(func.sum(FlakyTestStat.flaky_runs), 0),
            func.coalesce(func.sum(FlakyTestStat.double_reruns), 0),
            func.coalesce(func.sum(FlakyTestStat.passing_runs), 0)
        ).outerjoin(
            FlakyTestStat,
            and_(
                calendar.c.day == FlakyTestStat.date,
                FlakyTestStat.project_id == project_id
            )
        ).order_by(
            calendar.c.day.desc()
        ).group_by(
            calendar.c.day
        )

        chart_data = []
        for d, flaky_runs, double_reruns, passing_runs in historical_data:
            chart_data.append({
                'date': str(d.date()),
                'flaky_runs': flaky_runs,
                'double_reruns': double_reruns,
                'passing_runs': passing_runs
            })

        return chart_data
