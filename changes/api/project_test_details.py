from __future__ import absolute_import, division, unicode_literals

from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.api.serializer.models.testcase import GeneralizedTestCase
from changes.models import Build, Project, TestCase


class ProjectTestDetailsAPIView(APIView):
    def get(self, project_id, test_hash):
        project = Project.get(project_id)
        if not project:
            return '', 404

        # use the most recent test run to find basic details
        test = TestCase.query.filter(
            TestCase.project_id == project_id,
            TestCase.name_sha == test_hash,
        ).order_by(TestCase.date_created.desc()).limit(1).first()
        if not test:
            return '', 404

        first_test = TestCase.query.filter(
            TestCase.project_id == project_id,
            TestCase.name_sha == test_hash,
        ).order_by(TestCase.date_created.asc()).limit(1).first()
        first_build = Build.query.options(
            joinedload('author'),
            joinedload('source').joinedload('revision'),
        ).filter(
            Build.id == first_test.job.build_id,
        ).first()

        context = self.serialize(test, {
            TestCase: GeneralizedTestCase(),
        })
        context.update({
            'firstBuild': first_build,
        })

        return self.respond(context, serialize=False)
