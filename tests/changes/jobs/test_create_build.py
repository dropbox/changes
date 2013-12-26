from __future__ import absolute_import

import mock

from changes.config import db
from changes.jobs.create_build import create_build
from changes.models import Plan, Step, BuildFamily, JobPlan
from changes.testutils import TestCase


class CreateBuildTest(TestCase):
    @mock.patch('changes.jobs.create_build.queue.delay')
    @mock.patch('changes.backends.jenkins.builder.JenkinsBuilder.create_build')
    @mock.patch.object(Step, 'get_implementation')
    def test_simple(self, get_implementation, builder_create_build, queue_delay):
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

        family = BuildFamily(
            project=job.project,
            repository=job.repository,
            revision_sha=job.revision_sha,
            label=job.label,
            author=job.author,
            target=job.target,
        )
        db.session.add(family)

        jobplan = JobPlan(
            plan=plan,
            family=family,
            job=job,
            project=self.project,
        )
        db.session.add(jobplan)

        create_build(build_id=job.id.hex)

        get_implementation.assert_called_once_with()

        implementation.execute.assert_called_once_with(
            job=job,
        )

        assert len(builder_create_build.mock_calls) == 0

        # ensure signal is fired
        queue_delay.assert_called_once_with('sync_build', kwargs={
            'build_id': job.id.hex,
        }, countdown=5)

    @mock.patch('changes.jobs.create_build.queue.delay')
    @mock.patch('changes.backends.jenkins.builder.JenkinsBuilder.create_build')
    def test_without_build_plan(self, builder_create_build, queue_delay):
        job = self.create_job(self.project)

        create_build(build_id=job.id.hex)

        # build sync is abstracted via sync_with_builder
        builder_create_build.assert_called_once_with(job=job)

        # ensure signal is fired
        queue_delay.assert_called_once_with('sync_build', kwargs={
            'build_id': job.id.hex,
        }, countdown=5)
