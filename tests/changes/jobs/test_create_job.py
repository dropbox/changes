from __future__ import absolute_import

import mock

from changes.config import db
from changes.jobs.create_job import create_job
from changes.models import Plan, Step, Build, JobPlan
from changes.testutils import TestCase


class CreateBuildTest(TestCase):
    @mock.patch('changes.jobs.create_job.queue.delay')
    @mock.patch('changes.backends.jenkins.builder.JenkinsBuilder.create_job')
    @mock.patch.object(Step, 'get_implementation')
    def test_simple(self, get_implementation, builder_create_job, queue_delay):
        implementation = mock.Mock()
        get_implementation.return_value = implementation

        job = self.create_job(self.project)

        plan = Plan(
            label='test',
        )
        db.session.add(plan)

        step = Step(
            plan=plan,
            implementation='test',
            order=0,
        )
        db.session.add(step)

        build = Build(
            project=job.project,
            repository=job.repository,
            revision_sha=job.revision_sha,
            label=job.label,
            author=job.author,
            target=job.target,
        )
        db.session.add(build)

        jobplan = JobPlan(
            plan=plan,
            build=build,
            job=job,
            project=self.project,
        )
        db.session.add(jobplan)

        create_job(job_id=job.id.hex)

        get_implementation.assert_called_once_with()

        implementation.execute.assert_called_once_with(
            job=job,
        )

        assert len(builder_create_job.mock_calls) == 0

        # ensure signal is fired
        queue_delay.assert_called_once_with('sync_job', kwargs={
            'job_id': job.id.hex,
        }, countdown=5)

    @mock.patch('changes.jobs.create_job.queue.delay')
    @mock.patch('changes.backends.jenkins.builder.JenkinsBuilder.create_job')
    def test_without_build_plan(self, builder_create_job, queue_delay):
        job = self.create_job(self.project)

        create_job(job_id=job.id.hex)

        # job sync is abstracted via sync_with_builder
        builder_create_job.assert_called_once_with(job=job)

        # ensure signal is fired
        queue_delay.assert_called_once_with('sync_job', kwargs={
            'job_id': job.id.hex,
        }, countdown=5)
