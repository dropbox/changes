from __future__ import absolute_import

import mock
import responses

from changes.backends.jenkins.generic_builder import JenkinsGenericBuilder
from changes.backends.jenkins.buildsteps.collector import JenkinsCollectorBuildStep
from changes.constants import Status
from changes.models import JobPhase, JobStep
from changes.testutils import TestCase


class JenkinsCollectorBuildStepTest(TestCase):
    def get_buildstep(self):
        return JenkinsCollectorBuildStep(
            job_name='foo-bar',
            script='exit 0',
        )

    def get_mock_builder(self):
        return mock.Mock(spec=JenkinsGenericBuilder)

    def test_get_builder(self):
        builder = self.get_buildstep().get_builder()
        assert builder.job_name == 'foo-bar'
        assert builder.script == 'exit 0'

    @mock.patch.object(JenkinsCollectorBuildStep, 'get_builder')
    def test_default_artifact_handling(self, get_builder):
        builder = self.get_mock_builder()
        get_builder.return_value = builder

        build = self.create_build(self.project)
        job = self.create_job(build, data={
            'job_name': 'server',
            'build_no': '35',
        })
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data={
            'item_id': 13,
            'job_name': 'server',
        })
        artifact = {'fileName': 'junit.xml'}

        buildstep = self.get_buildstep()
        buildstep.fetch_artifact(step, artifact)

        builder.sync_artifact.assert_called_once_with(step, artifact)

    @responses.activate
    @mock.patch.object(JenkinsCollectorBuildStep, 'get_builder')
    def test_job_expansion(self, get_builder):
        """
        Fairly heavy integration test which mocks out a few things but ensures
        that generic APIs are called correctly and the jobs.json is parsed
        as expected.
        """
        builder = self.get_mock_builder()
        builder.fetch_artifact.return_value.json.return_value = {
            'phase': 'Run',
            'jobs': [
                {'name': 'Optional name',
                 'cmd': 'echo 1'},
                {'cmd': 'py.test --junit=junit.xml'},
            ],
        }
        builder.create_job_from_params.return_value = {
            'job_name': 'foo-bar',
            'build_no': 23,
        }

        get_builder.return_value = builder

        build = self.create_build(self.project)
        job = self.create_job(build, data={
            'job_name': 'server',
            'build_no': '35',
        })
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data={
            'item_id': 13,
            'job_name': 'server',
        })
        artifact = {
            'fileName': 'jobs.json',
        }

        buildstep = self.get_buildstep()
        buildstep.fetch_artifact(step, artifact)

        phase2 = JobPhase.query.filter(
            JobPhase.job_id == job.id,
            JobPhase.id != phase.id,
        ).first()

        assert phase2, 'phase wasnt created'
        assert phase2.label == 'Run'
        assert phase2.status == Status.queued

        new_steps = sorted(JobStep.query.filter(
            JobStep.phase_id == phase2.id
        ), key=lambda x: x.date_created)

        assert len(new_steps) == 2
        assert new_steps[0].label == 'Optional name'
        assert new_steps[0].data == {
            'build_no': 23,
            'job_name': 'foo-bar',
            'cmd': 'echo 1',
        }

        assert new_steps[1].label == 'a357e93d82b8627ba1aa5f5c58884cd8'
        assert new_steps[1].data == {
            'build_no': 23,
            'job_name': 'foo-bar',
            'cmd': 'py.test --junit=junit.xml',
        }

        builder.fetch_artifact.assert_called_once_with(step, artifact)
        builder.create_job_from_params.assert_any_call(
            job_name='foo-bar',
            job_id=new_steps[0].id.hex,
            params=builder.get_job_parameters.return_value,
        )
        builder.create_job_from_params.assert_any_call(
            job_name='foo-bar',
            job_id=new_steps[1].id.hex,
            params=builder.get_job_parameters.return_value,
        )
