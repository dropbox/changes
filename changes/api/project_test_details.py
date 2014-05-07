from __future__ import absolute_import, division, unicode_literals

from sqlalchemy.orm import contains_eager, joinedload

from changes.api.base import APIView
from changes.api.serializer.models.testcase import GeneralizedTestCase
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
            joinedload('job.build'),
            joinedload('job.build.author'),
            joinedload('job.build.source'),
            joinedload('job.build.source.revision'),
        ).join(
            job_sq, TestCase.job_id == job_sq.c.id,
        ).join(
            Source, job_sq.c.source_id == Source.id,
        ).filter(
            Source.repository_id == project.repository_id,
            Source.patch_id == None,  # NOQA
            Source.revision_sha != None,  # NOQA
            TestCase.name_sha == test.name_sha,
        ).order_by(job_sq.c.date_created.desc())[:25])

        first_test = TestCase.query.filter(
            TestCase.project_id == project_id,
            TestCase.name_sha == test_hash,
        ).order_by(TestCase.date_created.asc()).limit(1).first()
        first_build = Build.query.options(
            joinedload('author'),
            joinedload('source'),
        ).filter(
            Build.id == first_test.job.build_id,
        ).first()

        jobs = set(r.job for r in recent_runs)
        builds = set(j.build for j in jobs)

        serialized_jobs = dict(zip(jobs, self.serialize(jobs)))
        serialized_builds = dict(zip(builds, self.serialize(builds)))

        results = []
        for recent_run, s_recent_run in zip(recent_runs, self.serialize(recent_runs)):
            s_recent_run['job'] = serialized_jobs[recent_run.job]
            s_recent_run['job']['build'] = serialized_builds[recent_run.job.build]
            results.append(s_recent_run)

        context = self.serialize(test, {
            TestCase: GeneralizedTestCase(),
        })
        context.update({
            'results': results,
            'firstBuild': first_build,
        })

        return self.respond(context, serialize=False)
