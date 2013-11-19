from datetime import datetime, timedelta

from sqlalchemy import distinct
from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func

from changes.api.base import APIView
from changes.config import db
from changes.constants import Status, Result
from changes.models import TestGroup, Project, Build

SLOW_TEST_THRESHOLD = 1000  # 1 second


class ProjectStatsIndexAPIView(APIView):
    def _get_project(self, project_id):
        project = Project.query.options(
            joinedload(Project.repository),
        ).filter_by(slug=project_id).first()
        if project is None:
            project = Project.query.options(
                joinedload(Project.repository),
            ).get(project_id)
        return project

    def get(self, project_id):
        project = self._get_project(project_id)

        current_datetime = datetime.now()

        current_build = Build.query.options(
            joinedload(Build.project),
            joinedload(Build.author),
        ).filter(
            Build.revision_sha != None,  # NOQA
            Build.project == project,
            Build.status == Status.finished,
        ).order_by(
            Build.date_created.desc(),
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
            func.min(TestGroup.date_created) >= current_datetime - timedelta(days=7),
        ).subquery('t')

        # find current build tests which are still over threshold and match
        # our names
        new_slow_tests = db.session.query(TestGroup).filter(
            TestGroup.build_id == current_build.id,
            TestGroup.duration > SLOW_TEST_THRESHOLD,
            TestGroup.name_sha.in_(stmt),
        ).order_by(TestGroup.duration.desc()).limit(100)

        new_slow_tests = list(new_slow_tests)

        # TODO(dcramer): this could be done in a single query
        cutoff = current_datetime - timedelta(days=7)

        num_passes = Build.query.filter(
            Build.project_id == project.id,
            Build.status == Status.finished,
            Build.result == Result.passed,
            Build.date_created >= cutoff,
            Build.date_created < current_datetime,
        ).count()
        num_failures = Build.query.filter(
            Build.project_id == project.id,
            Build.status == Status.finished,
            Build.result == Result.failed,
            Build.date_created >= cutoff,
            Build.date_created < current_datetime,
        ).count()
        num_builds = Build.query.filter(
            Build.project_id == project.id,
            Build.status == Status.finished,
            Build.date_created >= cutoff,
            Build.date_created < current_datetime,
        ).count()

        num_authors = db.session.query(
            func.count(distinct(Build.author_id))
        ).filter(
            Build.project_id == project.id,
            Build.status == Status.finished,
            Build.date_created >= cutoff,
            Build.date_created < current_datetime,
        ).scalar()

        avg_build_time = db.session.query(
            func.avg(Build.duration).label('avg_build_time'),
        ).filter(
            Build.project_id == project.id,
            Build.status == Status.finished,
            Build.result == Result.passed,
            Build.duration > 0,
            Build.date_created >= cutoff,
            Build.date_created < current_datetime,
        ).scalar()
        if avg_build_time is not None:
            avg_build_time = float(avg_build_time)

        previous_cutoff = cutoff - timedelta(days=7)

        previous_num_passes = Build.query.filter(
            Build.project_id == project.id,
            Build.status == Status.finished,
            Build.result == Result.passed,
            Build.date_created >= previous_cutoff,
            Build.date_created < cutoff,
        ).count()
        previous_num_failures = Build.query.filter(
            Build.project_id == project.id,
            Build.status == Status.finished,
            Build.result == Result.failed,
            Build.date_created >= previous_cutoff,
            Build.date_created < cutoff,
        ).count()
        previous_num_builds = Build.query.filter(
            Build.project_id == project.id,
            Build.status == Status.finished,
            Build.date_created >= previous_cutoff,
            Build.date_created < cutoff,
        ).count()

        previous_avg_build_time = db.session.query(
            func.avg(Build.duration).label('avg_build_time'),
        ).filter(
            Build.project_id == project.id,
            Build.status == Status.finished,
            Build.result == Result.passed,
            Build.duration > 0,
            Build.date_created >= previous_cutoff,
            Build.date_created < cutoff,
        ).scalar()
        if previous_avg_build_time is not None:
            previous_avg_build_time = float(previous_avg_build_time)

        context = {
            'buildStats': {
                'period': [current_datetime, cutoff],
                'numFailed': num_failures,
                'numPassed': num_passes,
                'numBuilds': num_builds,
                'avgBuildTime': avg_build_time,
                'numAuthors': num_authors,
                'previousPeriod': {
                    'period': [cutoff, previous_cutoff],
                    'numFailed': previous_num_failures,
                    'numPassed': previous_num_passes,
                    'numBuilds': previous_num_builds,
                    'avgBuildTime': previous_avg_build_time,
                }
            },
            'newSlowTestGroups': new_slow_tests,
        }

        return self.respond(context)
