from __future__ import absolute_import

import json
import mock
import responses

from changes.artifacts.collection_artifact import JobsJsonHandler
from changes.backends.jenkins.buildsteps.collector import JenkinsCollectorBuilder, JenkinsCollectorBuildStep
from changes.config import db
from changes.constants import Result, Status
from changes.models import JobPhase, JobPlan, FailureReason
from changes.testutils import TestCase
from ..test_builder import BaseTestCase


class JenkinsCollectorBuilderTest(BaseTestCase):
    builder_cls = JenkinsCollectorBuilder
    builder_options = {
        'master_urls': ['http://jenkins.example.com'],
        'diff_urls': ['http://jenkins-diff.example.com'],
        'job_name': 'server',
        'script': 'echo hello',
        'cluster': 'server-runner',
    }

    def test_has_required_artifact(self):
        build = self.create_build(self.project)
        job = self.create_job(build)
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, status=Status.finished,
                                   result=Result.passed)

        artifacts = [self.create_artifact(step, 'manifest.json'),
                     self.create_artifact(step, 'foo/jobs.json')]

        builder = self.get_builder()
        builder.verify_final_artifacts(step, artifacts)

        assert step.result == Result.passed
        assert not FailureReason.query.filter(
            FailureReason.step_id == step.id,
        ).first()

    def test_missing_required_artifact(self):
        build = self.create_build(self.project)
        job = self.create_job(build)
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, status=Status.finished,
                                   result=Result.passed)

        artifacts = [self.create_artifact(step, 'manifest.json')]

        builder = self.get_builder()
        builder.verify_final_artifacts(step, artifacts)

        # No required artifact collected should cause the step to fail.
        assert step.result == Result.failed
        assert FailureReason.query.filter(
            FailureReason.step_id == step.id,
            FailureReason.reason == 'missing_artifact'
        ).first()


class JenkinsCollectorBuildStepTest(TestCase):
    def get_buildstep(self):
        return JenkinsCollectorBuildStep(
            jenkins_url=['http://jenkins.example.com'],
            job_name='foo-bar',
            script='exit 0',
            cluster='default',
        )

    def get_mock_builder(self):
        return mock.Mock(spec=JenkinsCollectorBuilder)

    def test_get_builder(self):
        builder = self.get_buildstep().get_builder()
        assert builder.job_name == 'foo-bar'
        assert builder.script == 'exit 0'

    @mock.patch.object(JenkinsCollectorBuildStep, 'get_builder')
    def test_default_artifact_handling(self, get_builder):
        builder = self.get_mock_builder()
        builder.get_required_handler.return_value = JobsJsonHandler
        get_builder.return_value = builder

        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build, data={
            'job_name': 'server',
            'build_no': '35',
        })
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data={
            'item_id': 13,
            'job_name': 'server',
        })

        artifact = self.create_artifact(
            step=step,
            name='junit.xml',
            data={'fileName': 'junit.xml'},
        )

        buildstep = self.get_buildstep()
        buildstep.fetch_artifact(artifact)

        builder.sync_artifact.assert_called_once_with(artifact)

    @responses.activate
    @mock.patch.object(JenkinsCollectorBuilder, 'fetch_artifact')
    @mock.patch.object(JenkinsCollectorBuilder, 'create_jenkins_job_from_params')
    @mock.patch.object(JenkinsCollectorBuilder, 'get_job_parameters')
    def test_job_expansion(self, get_job_parameters,
                           create_jenkins_job_from_params, fetch_artifact):
        """
        Fairly heavy integration test which mocks out a few things but ensures
        that generic APIs are called correctly and the jobs.json is parsed
        as expected.
        """
        fetch_artifact.return_value.content = json.dumps({
            'phase': 'Run',
            'jobs': [
                {'name': 'Optional name',
                 'cmd': 'echo 1'},
                {'cmd': 'py.test --junit=junit.xml'},
            ],
        })
        create_jenkins_job_from_params.return_value = {
            'job_name': 'foo-bar',
            'build_no': 23,
        }

        get_job_parameters.return_value = {'PARAM': '44'}

        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build, data={
            'job_name': 'server',
            'build_no': '35',
        })
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data={
            'item_id': 13,
            'job_name': 'server',
        })

        artifact = self.create_artifact(
            step=step,
            name='jobs.json',
            data={'fileName': 'jobs.json'},
        )

        buildstep = self.get_buildstep()
        with mock.patch.object(JobPlan, 'get_build_step_for_job') as get_build_step_for_job:
            get_build_step_for_job.return_value = (None, buildstep)
            buildstep.fetch_artifact(artifact)

        phase2 = JobPhase.query.filter(
            JobPhase.job_id == job.id,
            JobPhase.id != phase.id,
        ).first()

        assert phase2, 'phase wasnt created'
        assert phase2.label == 'Run'
        assert phase2.status == Status.queued

        new_steps = sorted(phase2.current_steps, key=lambda x: x.date_created)

        assert len(new_steps) == 2
        assert new_steps[0].label == 'Optional name'
        assert new_steps[0].data == {
            'build_no': 23,
            'job_name': 'foo-bar',
            'cmd': 'echo 1',
            'expanded': True,
        }

        assert new_steps[1].label == 'a357e93d82b8627ba1aa5f5c58884cd8'
        assert new_steps[1].data == {
            'build_no': 23,
            'job_name': 'foo-bar',
            'cmd': 'py.test --junit=junit.xml',
            'expanded': True,
        }

        fetch_artifact.assert_called_once_with(artifact.step, artifact.data)
        create_jenkins_job_from_params.assert_any_call(
            job_name='foo-bar',
            changes_bid=new_steps[0].id.hex,
            params=[{'name': 'PARAM', 'value': '44'}],
            is_diff=False
        )
        create_jenkins_job_from_params.assert_any_call(
            job_name='foo-bar',
            changes_bid=new_steps[1].id.hex,
            params=[{'name': 'PARAM', 'value': '44'}],
            is_diff=False
        )

    @responses.activate
    @mock.patch.object(JenkinsCollectorBuilder, 'fetch_artifact')
    @mock.patch.object(JenkinsCollectorBuilder, 'create_jenkins_job_from_params')
    @mock.patch.object(JenkinsCollectorBuilder, 'get_job_parameters')
    def test_create_replacement_jobstep(self, get_job_parameters,
                           create_jenkins_job_from_params, fetch_artifact):
        """
        Tests create_replacement_jobstep by running a very similar test to
        test_job_expansion, failing one of the jobsteps and then replacing it,
        and making sure the results still end up the same.
        """
        fetch_artifact.return_value.content = json.dumps({
            'phase': 'Run',
            'jobs': [
                {'name': 'Optional name',
                 'cmd': 'echo 1'},
                {'cmd': 'py.test --junit=junit.xml'},
            ],
        })
        create_jenkins_job_from_params.return_value = {
            'job_name': 'foo-bar',
            'build_no': 23,
        }

        get_job_parameters.return_value = {'PARAM': '44'}

        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build, data={
            'job_name': 'server',
            'build_no': '35',
        })
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data={
            'item_id': 13,
            'job_name': 'server',
        })

        artifact = self.create_artifact(
            step=step,
            name='jobs.json',
            data={'fileName': 'jobs.json'},
        )

        buildstep = self.get_buildstep()
        with mock.patch.object(JobPlan, 'get_build_step_for_job') as get_build_step_for_job:
            get_build_step_for_job.return_value = (None, buildstep)
            buildstep.fetch_artifact(artifact)

        phase2 = JobPhase.query.filter(
            JobPhase.job_id == job.id,
            JobPhase.id != phase.id,
        ).first()

        assert phase2, 'phase wasnt created'
        assert phase2.label == 'Run'
        assert phase2.status == Status.queued

        new_steps = sorted(phase2.current_steps, key=lambda x: x.date_created)

        failstep = new_steps[1]
        failstep.result = Result.infra_failed
        failstep.status = Status.finished
        db.session.add(failstep)
        db.session.commit()

        replacement_step = buildstep.create_replacement_jobstep(failstep)
        # new jobstep should still be part of same job/phase
        assert replacement_step.job == job
        assert replacement_step.phase == phase2
        # make sure .steps actually includes the new jobstep
        assert len(phase2.steps) == 3
        # make sure replacement id is correctly set
        assert failstep.replacement_id == replacement_step.id

        # Now perform same tests as test_job_expansion, making sure that the
        # replacement step still satisfies all the correct attributes
        new_steps = sorted(phase2.current_steps, key=lambda x: x.date_created)
        assert new_steps[1] == replacement_step

        assert len(new_steps) == 2
        assert new_steps[0].label == 'Optional name'
        assert new_steps[0].data == {
            'build_no': 23,
            'job_name': 'foo-bar',
            'cmd': 'echo 1',
            'expanded': True,
        }

        assert new_steps[1].label == 'a357e93d82b8627ba1aa5f5c58884cd8'
        assert new_steps[1].data == {
            'build_no': 23,
            'job_name': 'foo-bar',
            'cmd': 'py.test --junit=junit.xml',
            'expanded': True,
        }

        fetch_artifact.assert_called_once_with(artifact.step, artifact.data)
        create_jenkins_job_from_params.assert_any_call(
            job_name='foo-bar',
            changes_bid=new_steps[0].id.hex,
            params=[{'name': 'PARAM', 'value': '44'}],
            is_diff=False
        )
        create_jenkins_job_from_params.assert_any_call(
            job_name='foo-bar',
            changes_bid=new_steps[1].id.hex,
            params=[{'name': 'PARAM', 'value': '44'}],
            is_diff=False
        )
