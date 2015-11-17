from __future__ import absolute_import

import json
import mock
import responses

from uuid import UUID

from changes.backends.jenkins.buildsteps.collector import JenkinsCollectorBuilder, JenkinsCollectorBuildStep
from changes.config import db
from changes.constants import Result, Status
from changes.models import JobPhase, JobPlan
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

    @responses.activate
    def test_no_jobs_collected(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/api/json/',
            body=self.load_fixture('fixtures/GET/job_details_success.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/logText/progressiveText/?start=0',
            match_querystring=True,
            adding_headers={'X-Text-Size': '0'},
            body='')
        responses.add(
            responses.GET,
            'http://jenkins.example.com/computer/server-ubuntu-10.04%20(ami-746cf244)%20(i-836023b7)/config.xml',
            body=self.load_fixture('fixtures/GET/node_config.xml'))

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data={
            'build_no': 2,
            'item_id': 13,
            'job_name': 'server',
            'queued': False,
            'master': 'http://jenkins.example.com',
        })

        builder = self.get_builder()
        builder.sync_step(step)

        # No jobs.json collected should cause the step to fail.
        assert step.result == Result.failed


class JenkinsCollectorBuildStepTest(TestCase):
    def get_buildstep(self):
        return JenkinsCollectorBuildStep(
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
        builder.get_required_artifact.return_value = 'required.json'
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

        builder.sync_artifact.assert_called_once_with(artifact, sync_logs=False)

    @responses.activate
    @mock.patch.object(JenkinsCollectorBuilder, 'fetch_artifact')
    @mock.patch.object(JenkinsCollectorBuilder, 'create_jenkins_job_from_params')
    @mock.patch.object(JenkinsCollectorBuilder, 'get_required_artifact')
    @mock.patch.object(JenkinsCollectorBuilder, 'get_job_parameters')
    def test_job_expansion(self, get_job_parameters, get_required_artifact,
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
        get_required_artifact.return_value = 'jobs.json'

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
    @mock.patch.object(JenkinsCollectorBuilder, 'get_required_artifact')
    @mock.patch.object(JenkinsCollectorBuilder, 'get_job_parameters')
    def test_create_replacement_jobstep(self, get_job_parameters, get_required_artifact,
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
        get_required_artifact.return_value = 'jobs.json'

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
