from cStringIO import StringIO

import mock

from changes.artifacts.collection_artifact import CollectionArtifactHandler
from changes.models import FailureReason, JobPlan
from changes.testutils import TestCase


class CollectionArtifactHandlerTest(TestCase):
    @mock.patch.object(JobPlan, 'get_build_step_for_job')
    def test_valid_json(self, get_build_step_for_job):
        buildstep = mock.Mock()
        get_build_step_for_job.return_value = (None, buildstep)
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)
        handler = CollectionArtifactHandler(jobstep)
        handler.FILENAMES = ('tests.json',)

        handler.process(StringIO("{}"))
        buildstep.expand_jobs.assert_called_once_with(jobstep, {})
        assert not FailureReason.query.filter(FailureReason.step_id == jobstep.id).first()

    @mock.patch.object(JobPlan, 'get_build_step_for_job')
    def test_invalid_json(self, get_build_step_for_job):
        buildstep = mock.Mock()
        get_build_step_for_job.return_value = (None, buildstep)
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)
        handler = CollectionArtifactHandler(jobstep)
        handler.FILENAMES = ('tests.json',)

        handler.process(StringIO(""))
        assert buildstep.call_count == 0
        assert FailureReason.query.filter(FailureReason.step_id == jobstep.id).first()
