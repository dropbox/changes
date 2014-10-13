from __future__ import absolute_import

import mock

from changes.jobs.create_job import create_job
from changes.models import HistoricalImmutableStep
from changes.testutils import TestCase


class CreateJobTest(TestCase):
    @mock.patch('changes.jobs.create_job.sync_job')
    @mock.patch.object(HistoricalImmutableStep, 'get_implementation')
    def test_simple(self, get_implementation, sync_job):
        implementation = mock.Mock()
        get_implementation.return_value = implementation

        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        plan = self.create_plan(project)
        self.create_step(plan)
        self.create_job_plan(job, plan)

        create_job(
            job_id=job.id.hex,
            task_id=job.id.hex,
            parent_task_id=build.id.hex,
        )

        get_implementation.assert_called_once_with()

        implementation.execute.assert_called_once_with(
            job=job,
        )

        sync_job.delay.assert_called_once_with(
            job_id=job.id.hex,
            task_id=job.id.hex,
            parent_task_id=build.id.hex,
        )
