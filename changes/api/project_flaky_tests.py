from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse

from changes.api.base import APIView
from changes.config import db
from changes.models import FlakyTestStat, Project, TestCase


class ProjectFlakyTestsAPIView(APIView):
    parser = reqparse.RequestParser()

    def get(self, project_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        last_date = db.session.query(
            FlakyTestStat.end_date
        ).order_by(
            FlakyTestStat.end_date.desc()
        ).limit(1).scalar()

        query = db.session.query(
            FlakyTestStat, TestCase
        ).join(
            TestCase
        ).filter(
            FlakyTestStat.end_date == last_date,
            FlakyTestStat.project_id == project_id
        ).order_by(
            FlakyTestStat.flaky_runs.desc()
        )

        flaky_tests = []
        for flaky_test, last_flaky_run in query:
            flaky_tests.append({
                'name': last_flaky_run.short_name,
                'package': last_flaky_run.package,
                'hash': last_flaky_run.name_sha,
                'flaky_runs': flaky_test.flaky_runs,
                'passing_runs': flaky_test.passing_runs
            })

        data = {
            'lastUpdate': str(last_date),
            'flakyTests': flaky_tests
        }

        return self.respond(data, serialize=False)
