from __future__ import absolute_import

import mock

from changes.jobs.sync_artifact import sync_artifact
from changes.models import Step
from changes.testutils import TestCase


class SyncArtifactTest(TestCase):
    def setUp(self):
        super(SyncArtifactTest, self).setUp()
        self.project = self.create_project()
        self.build = self.create_build(project=self.project)
        self.job = self.create_job(build=self.build)
        self.jobphase = self.create_jobphase(self.job)
        self.jobstep = self.create_jobstep(self.jobphase)
        self.artifact = self.create_artifact(self.jobstep, name='foo', data={
            'foo': 'bar',
        })

        self.plan = self.create_plan()
        self.plan.projects.append(self.project)
        self.step = self.create_step(self.plan, implementation='test', order=0)
        self.jobplan = self.create_job_plan(self.job, self.plan)

    @mock.patch.object(Step, 'get_implementation')
    def test_simple(self, get_implementation):
        implementation = mock.Mock()
        get_implementation.return_value = implementation

        sync_artifact(artifact_id=self.artifact.id.hex)

        implementation.fetch_artifact.assert_called_once_with(
            step=self.jobstep,
            artifact=self.artifact.data,
        )
