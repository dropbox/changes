from __future__ import absolute_import, division, unicode_literals

from sqlalchemy.orm import contains_eager, joinedload

from changes.api.base import APIView
from changes.api.serializer.models.job import JobWithBuildSerializer
from changes.api.serializer.models.testcase import (
    TestCaseWithJobSerializer, GeneralizedTestCase
)
from changes.constants import Status
from changes.models import Build, Project, TestCase, Job, Source


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

        # restrict the join to the last 1000 jobs otherwise this can get
        # significantly expensive as we have to seek quite a ways
        job_sq = Job.query.filter(
            Job.status == Status.finished,
            Job.project_id == project_id,
        ).order_by(Job.date_created.desc()).limit(1000).subquery()

        recent_runs = list(TestCase.query.options(
            contains_eager('job', alias=job_sq),
            contains_eager('job.source'),
            joinedload('job', 'build'),
        ).join(
            job_sq, TestCase.job_id == job_sq.c.id,
        ).join(
            Source, job_sq.c.source_id == Source.id,
        ).filter(
            Source.patch_id == None,  # NOQA
            Source.revision_sha != None,  # NOQA
            TestCase.name_sha == test.name_sha,
        ).order_by(job_sq.c.date_created.desc())[:25])

        first_build = Build.query.join(
            Job, Job.build_id == Build.id,
        ).join(
            TestCase, TestCase.job_id == Job.id,
        ).filter(
            TestCase.project_id == project_id,
            TestCase.name_sha == test_hash,
        ).order_by(TestCase.date_created.asc()).limit(1).first()

        extended_serializers = {
            TestCase: TestCaseWithJobSerializer(),
            Job: JobWithBuildSerializer(),
        }

        context = self.serialize(test, {
            TestCase: GeneralizedTestCase(),
        })
        context.update({
            'results': self.serialize(recent_runs, extended_serializers),
            'firstBuild': first_build,
        })

        return self.respond(context, serialize=False)
