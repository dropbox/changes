from __future__ import absolute_import

import mock

from changes.backends.jenkins.builder import JenkinsBuilder
from changes.backends.jenkins.buildstep import JenkinsBuildStep, JenkinsGenericBuildStep
from changes.models.snapshot import SnapshotStatus
from changes.testutils import TestCase


class JenkinsBuildStepTest(TestCase):
    def get_buildstep(self):
        return JenkinsBuildStep(job_name='foo-bar')

    def test_get_resource_limits(self):
        buildstep = JenkinsBuildStep(job_name="both", cpus=8, memory=8080)
        assert buildstep.get_resource_limits() == {
            'cpus': 8,
            'memory': 8080,
        }

        # We specify defaults, so if you don't want a limit, gotta say so.
        only_cpus = JenkinsBuildStep(job_name="only_cpus", cpus=8, memory=None)
        assert only_cpus.get_resource_limits() == {'cpus': 8}

        assert JenkinsBuildStep(job_name="defaults").get_resource_limits() == {
            "memory": 8192,
            "cpus": 4,
        }

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
        artifact = self.create_artifact(step, name='foo.log')

        buildstep = self.get_buildstep()
        buildstep.fetch_artifact(artifact)

        builder.sync_artifact.assert_called_once_with(artifact, sync_logs=False)


class JenkinsGenericBuildStepTest(TestCase):
    def get_buildstep(self):
        return JenkinsGenericBuildStep(job_name='foo-bar', script='script',
            cluster='cluster')

    @mock.patch.object(JenkinsGenericBuildStep, 'get_builder')
    def test_fetch_artifact_snapshot_image_status(self, get_builder):
        builder = mock.Mock()
        get_builder.return_value = builder

        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        plan = self.create_plan(project)
        snapshot = self.create_snapshot(project)
        snapshot_image = self.create_snapshot_image(snapshot, plan, job=job)

        artifact = mock.Mock()
        artifact.data = {'fileName': '/snapshot_status.json'}
        artifact_data = mock.Mock()
        artifact_data.json.return_value = {
            'image': snapshot_image.id,
            'status': 'active'
        }
        builder.fetch_artifact.return_value = artifact_data

        buildstep = self.get_buildstep()
        buildstep.fetch_artifact(artifact)

        assert snapshot_image.status == SnapshotStatus.active
