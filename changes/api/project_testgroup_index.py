from datetime import datetime, timedelta

from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func

from changes.api.base import APIView
from changes.config import db
from changes.constants import Status
from changes.models import TestGroup, Project, Build

SLOW_TEST_THRESHOLD = 1000  # 1 second


class ProjectTestGroupIndexAPIView(APIView):
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
            func.min(TestGroup.date_created) >= datetime.now() - timedelta(days=7),
        ).subquery('t')

        # find current build tests which are still over threshold and match
        # our names
        new_slow_tests = db.session.query(TestGroup).filter(
            TestGroup.build_id == current_build.id,
            TestGroup.duration > SLOW_TEST_THRESHOLD,
            TestGroup.name_sha.in_(stmt),
        ).order_by(TestGroup.duration.desc()).limit(100)

        new_slow_tests = list(new_slow_tests)

        context = {
            'newSlowTestGroups': new_slow_tests,
        }

        return self.respond(context)
