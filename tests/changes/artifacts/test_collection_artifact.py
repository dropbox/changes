from cStringIO import StringIO

import mock

from changes.artifacts.base import ArtifactParseError
from changes.artifacts.collection_artifact import CollectionArtifactHandler
from changes.config import db
from changes.constants import Result
from changes.models.failurereason import FailureReason
from changes.models.jobplan import JobPlan
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
        artifact = self.create_artifact(jobstep, 'tests.json')
        handler = CollectionArtifactHandler(jobstep)
        handler.FILENAMES = ('/tests.json',)

        handler.process(StringIO("{}"), artifact)
        buildstep.expand_jobs.assert_called_once_with(jobstep, {})
        # make sure changes were committed
        db.session.rollback()
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
        artifact = self.create_artifact(jobstep, 'tests.json')
        handler = CollectionArtifactHandler(jobstep)
        handler.FILENAMES = ('/tests.json',)

        handler.process(StringIO(""), artifact)
        assert buildstep.call_count == 0
        # make sure changes were committed
        db.session.rollback()
        assert FailureReason.query.filter(FailureReason.step_id == jobstep.id).first()

    @mock.patch.object(JobPlan, 'get_build_step_for_job')
    def test_parse_error(self, get_build_step_for_job):
        buildstep = mock.Mock()
        get_build_step_for_job.return_value = (None, buildstep)
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)
        artifact = self.create_artifact(jobstep, 'tests.json')
        handler = CollectionArtifactHandler(jobstep)
        handler.FILENAMES = ('/tests.json',)
        buildstep.expand_jobs.side_effect = ArtifactParseError('bad file')

        handler.process(StringIO("{}"), artifact)
        buildstep.expand_jobs.assert_called_once_with(jobstep, {})
        # make sure changes were committed
        db.session.rollback()
        assert FailureReason.query.filter(FailureReason.step_id == jobstep.id).first()

    @mock.patch.object(JobPlan, 'get_build_step_for_job')
    def test_expand_jobs_error(self, get_build_step_for_job):
        buildstep = mock.Mock()
        get_build_step_for_job.return_value = (None, buildstep)
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)
        artifact = self.create_artifact(jobstep, 'tests.json')
        handler = CollectionArtifactHandler(jobstep)
        handler.FILENAMES = ('/tests.json',)
        buildstep.expand_jobs.side_effect = Exception('error')

        handler.process(StringIO("{}"), artifact)
        buildstep.expand_jobs.assert_called_once_with(jobstep, {})
        # make sure changes were committed
        db.session.rollback()
        assert jobstep.result == Result.infra_failed
        assert not FailureReason.query.filter(FailureReason.step_id == jobstep.id).first()
