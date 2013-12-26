from changes.config import db
from changes.constants import Cause
from changes.models import Job, JobPlan
from changes.testutils import APITestCase


class BuildRetryTest(APITestCase):
    def test_simple(self):
        change = self.create_change(self.project)
        job = self.create_job(self.project, change=change)

        path = '/api/0/builds/{0}/retry/'.format(job.id.hex)
        resp = self.client.post(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['build']['id']
        assert data['build']['link']
        new_job = Job.query.get(data['build']['id'])
        assert new_job.id != job.id
        assert new_job.change == change
        assert new_job.project == self.project
        assert new_job.cause == Cause.retry
        assert new_job.parent_id == job.id
        assert new_job.revision_sha == job.revision_sha
        assert new_job.author_id == job.author_id
        assert new_job.label == job.label
        assert new_job.message == job.message
        assert new_job.target == job.target

    def test_with_buildplan(self):
        plan = self.create_plan()
        plan.projects.append(self.project)

        change = self.create_change(self.project)
        job = self.create_job(self.project, change=change)

        build = self.create_build_from_job(job)

        jobplan = JobPlan(
            build=build,
            job=job,
            plan=plan,
            project=self.project,
        )
        db.session.add(jobplan)

        path = '/api/0/builds/{0}/retry/'.format(job.id.hex)
        resp = self.client.post(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['build']['id']
        assert data['build']['link']
        new_job = Job.query.get(data['build']['id'])
        assert new_job.id != job.id
        assert new_job.change == change
        assert new_job.project == self.project
        assert new_job.cause == Cause.retry
        assert new_job.parent_id == job.id
        assert new_job.revision_sha == job.revision_sha
        assert new_job.author_id == job.author_id
        assert new_job.label == job.label
        assert new_job.message == job.message
        assert new_job.target == job.target

        new_jobplan = JobPlan.query.filter(
            JobPlan.job_id == new_job.id
        ).first()

        assert new_jobplan.build_id == build.id
        assert new_jobplan.plan_id == plan.id
        assert new_jobplan.project_id == self.project.id
