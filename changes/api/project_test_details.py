from __future__ import absolute_import, division, unicode_literals

from changes.api.base import APIView, error
from changes.api.serializer.models.testcase import GeneralizedTestCase
from changes.models.project import Project
from changes.models.test import TestCase


class ProjectTestDetailsAPIView(APIView):
    def get(self, project_id, test_hash):
        project = Project.get(project_id)
        if not project:
            return error("Project not found", http_code=404)

        # use the most recent test run to find basic details
        test = TestCase.query.filter(
            TestCase.project_id == project.id,
            TestCase.name_sha == test_hash,
        ).order_by(TestCase.date_created.desc()).limit(1).first()
        if not test:
            return error("Test not found", http_code=404)

        context = self.serialize(test, {
            TestCase: GeneralizedTestCase(),
        })

        return self.respond(context)
