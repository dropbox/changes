from __future__ import absolute_import

import mock

from cStringIO import StringIO

from changes.config import db
from changes.jobs.sync_artifact import sync_artifact
from changes.models import HistoricalImmutableStep
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

        self.plan = self.create_plan(self.project)
        self.step = self.create_step(self.plan, implementation='test', order=0)
        self.jobplan = self.create_job_plan(self.job, self.plan)

    @mock.patch.object(HistoricalImmutableStep, 'get_implementation')
    def test_file_doesnt_exist(self, get_implementation):
        implementation = mock.Mock()
        get_implementation.return_value = implementation

        with mock.patch.object(sync_artifact, 'allow_absent_from_db', True):
            sync_artifact(artifact_id=self.artifact.id.hex)

        implementation.fetch_artifact.assert_called_once_with(
            artifact=self.artifact,
        )

    @mock.patch.object(HistoricalImmutableStep, 'get_implementation')
    def test_file_exists(self, get_implementation):
        implementation = mock.Mock()
        get_implementation.return_value = implementation
        manager = mock.Mock()
        implementation.get_artifact_manager.return_value = manager

        self.artifact.file.save(StringIO(), 'foo')
        db.session.add(self.artifact)
        db.session.commit()

        with mock.patch.object(sync_artifact, 'allow_absent_from_db', True):
            sync_artifact(artifact_id=self.artifact.id.hex)

        implementation.get_artifact_manager.assert_called_once_with(self.jobstep)
        manager.process.assert_called_once_with(self.artifact)
