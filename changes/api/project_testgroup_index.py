from datetime import datetime, timedelta

from sqlalchemy.orm import joinedload
from sqlalchemy.sql import func

from changes.api.base import APIView
from changes.api.serializer.models.testgroup import TestGroupWithBuildSerializer
from changes.config import db
from changes.models import TestGroup, Project

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

        stmt = db.session.query(
            TestGroup, func.min(TestGroup.date_created).label('first_seen')
        ).filter(
            TestGroup.project_id == project.id,
            TestGroup.num_leaves == 0,
            TestGroup.duration > SLOW_TEST_THRESHOLD,
        ).group_by(TestGroup).subquery('t')

        new_slow_tests = list(db.session.query(TestGroup).select_from(stmt).filter(
            stmt.c.first_seen >= datetime.now() - timedelta(days=7),
        ).options(
            joinedload(TestGroup.build),
        ).order_by(stmt.c.first_seen.desc()).limit(100))

        extended_serializers = {
            TestGroup: TestGroupWithBuildSerializer(),
        }

        context = {
            'newSlowTestGroups': self.serialize(new_slow_tests, extended_serializers),
        }

        return self.respond(context)
