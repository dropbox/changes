from __future__ import absolute_import, division, unicode_literals

from changes.api.base import APIView
from changes.api.serializer.models.testcase import GeneralizedTestCase
from changes.constants import Result, Status
from changes.models import Project, TestCase, Job, Source


class ProjectTestIndexAPIView(APIView):
    def get(self, project_id):
        project = Project.get(project_id)
        if not project:
            return '', 404

        latest_job = Job.query.join(
            Source, Source.id == Job.source_id,
        ).filter(
            Source.patch_id == None,  # NOQA
            Job.project_id == project.id,
            Job.result == Result.passed,
            Job.status == Status.finished,
        ).order_by(
            Job.date_created.desc(),
        ).limit(1).first()

        if not latest_job:
            return self.respond([])

        # use the most recent test
        results = TestCase.query.filter(
            TestCase.project_id == project_id,
            TestCase.job_id == latest_job.id,
        ).order_by(TestCase.duration.desc())

        return self.paginate(results, serializers={
            TestCase: GeneralizedTestCase(),
        })
