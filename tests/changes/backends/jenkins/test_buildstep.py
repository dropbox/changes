from __future__ import absolute_import

import mock

from changes.backends.jenkins.builder import JenkinsBuilder
from changes.backends.jenkins.buildstep import JenkinsBuildStep
from changes.testutils import TestCase


class JenkinsBuildStepTest(TestCase):
    def get_buildstep(self):
        return JenkinsBuildStep(job_name='foo-bar')

    def test_get_builder(self):
        buildstep = self.get_buildstep()
        builder = buildstep.get_builder()
        assert builder.job_name == 'foo-bar'
        assert type(builder) == JenkinsBuilder

    @mock.patch.object(JenkinsBuildStep, 'get_builder')
    def test_execute(self, get_builder):
        builder = mock.Mock()
        get_builder.return_value = builder

        build = self.create_build(self.create_project())
        job = self.create_job(build)

        buildstep = self.get_buildstep()
        buildstep.execute(job)

        builder.create_job.assert_called_once_with(job)

    @mock.patch.object(JenkinsBuildStep, 'get_builder')
    def test_update(self, get_builder):
        builder = mock.Mock()
        get_builder.return_value = builder

        build = self.create_build(self.create_project())
        job = self.create_job(build, data={
            'job_name': 'server',
            'build_no': '35',
        })

        buildstep = self.get_buildstep()
        buildstep.update(job)

        builder.sync_job.assert_called_once_with(job)

    @mock.patch.object(JenkinsBuildStep, 'get_builder')
    def test_update_step(self, get_builder):
        builder = mock.Mock()
        get_builder.return_value = builder

        build = self.create_build(self.create_project())
        job = self.create_job(build, data={
            'job_name': 'server',
            'build_no': '35',
        })
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data={
            'item_id': 13,
            'job_name': 'server',
        })

        buildstep = self.get_buildstep()
        buildstep.update_step(step)

        builder.sync_step.assert_called_once_with(step)

    @mock.patch.object(JenkinsBuildStep, 'get_builder')
    def test_cancel_step(self, get_builder):
        builder = mock.Mock()
        get_builder.return_value = builder

        build = self.create_build(self.create_project())
        job = self.create_job(build, data={
            'job_name': 'server',
            'build_no': '35',
        })
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data={
            'item_id': 13,
            'job_name': 'server',
        })

        buildstep = self.get_buildstep()
        buildstep.cancel_step(step)

        builder.cancel_step.assert_called_once_with(step)

    @mock.patch.object(JenkinsBuildStep, 'get_builder')
    def test_fetch_artifact(self, get_builder):
        builder = mock.Mock()
        get_builder.return_value = builder

        build = self.create_build(self.create_project())
        job = self.create_job(build, data={
            'job_name': 'server',
            'build_no': '35',
        })
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data={
            'item_id': 13,
            'job_name': 'server',
        })
        artifact = {'foo': 'bar'}

        buildstep = self.get_buildstep()
        buildstep.fetch_artifact(step, artifact)

        builder.sync_artifact.assert_called_once_with(step, artifact)
