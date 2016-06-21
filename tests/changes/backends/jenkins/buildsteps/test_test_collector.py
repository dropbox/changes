from __future__ import absolute_import

from flask import current_app

import json
import mock
import responses

from copy import deepcopy
from uuid import uuid4


from changes.artifacts.collection_artifact import TestsJsonHandler
from changes.backends.jenkins.buildsteps.test_collector import JenkinsTestCollectorBuilder, \
    JenkinsTestCollectorBuildStep
from changes.config import db
from changes.constants import Result, Status
from changes.expanders.tests import TestsExpander
from changes.lib.artifact_store_mock import ArtifactStoreMock
from changes.models.failurereason import FailureReason
from changes.models.jobphase import JobPhase
from changes.models.jobplan import JobPlan
from changes.models.jobstep import JobStep
from changes.testutils import TestCase
from ..test_builder import BaseTestCase


class JenkinsTestCollectorBuilderTest(BaseTestCase):
    builder_cls = JenkinsTestCollectorBuilder
    builder_options = {
        'master_urls': ['http://jenkins.example.com'],
        'diff_urls': ['http://jenkins-diff.example.com'],
        'job_name': 'server',
        'script': 'echo hello',
        'cluster': 'server-runner',
        'shard_build_type': 'legacy',
    }

    def setUp(self):
        super(JenkinsTestCollectorBuilderTest, self).setUp()
        self.old_config = deepcopy(current_app.config)

    def tearDown(self):
        current_app.config = self.old_config
        super(JenkinsTestCollectorBuilderTest, self).tearDown()

    def test_has_required_artifact(self):
        build = self.create_build(self.project)
        job = self.create_job(build)
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, status=Status.finished,
                                   result=Result.passed)

        artifacts = [self.create_artifact(step, 'manifest.json'),
                     self.create_artifact(step, 'artifactstore/tests.json')]

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

        artifacts = [self.create_artifact(step, 'manifest.json'),
                     self.create_artifact(step, 'foo/tests.json')]

        builder = self.get_builder()
        builder.verify_final_artifacts(step, artifacts)

        # No required artifact collected should cause the step to fail.
        assert step.result == Result.failed
        assert FailureReason.query.filter(
            FailureReason.step_id == step.id,
            FailureReason.reason == 'missing_artifact'
        ).first()

    def test_shard_lxc_config(self):
        current_app.config['CHANGES_CLIENT_BUILD_TYPES']['lxc_collect'] = {
            'uses_client': True,
            'adapter': 'lxc',
            'pre-launch': 'collect-prelaunch.sh',
            'jenkins-command': 'command',
            'commands': [{'script': 'script1'}]
        }
        current_app.config['CHANGES_CLIENT_BUILD_TYPES']['lxc'] = {
            'uses_client': True,
            'adapter': 'lxc',
            'pre-launch': 'shard-prelaunch.sh',
            'jenkins-command': 'command',
            'commands': [{'script': 'script1'}]
        }

        builder = self.get_builder(build_type='lxc_collect', shard_build_type='lxc')

        collect_jobstep = mock.Mock()
        collect_jobstep.job_id = uuid4()
        collect_jobstep.data = {}
        collect_config = builder.get_lxc_config(jobstep=collect_jobstep)
        assert collect_config.prelaunch == 'collect-prelaunch.sh'

        shard_jobstep = mock.Mock()
        shard_jobstep.job_id = uuid4()
        shard_jobstep.data = {'expanded': True}
        shard_config = builder.get_lxc_config(jobstep=shard_jobstep)
        assert shard_config.prelaunch == 'shard-prelaunch.sh'


class JenkinsTestCollectorBuildStepTest(TestCase):
    def get_buildstep(self):
        return JenkinsTestCollectorBuildStep(
            jenkins_url=['http://jenkins.example.com'],
            job_name='foo-bar',
            script='exit 0',
            cluster='default',
            max_shards=2,
            collection_build_type='legacy',
            build_type='legacy_2'
        )

    def get_mock_builder(self):
        return mock.Mock(spec=JenkinsTestCollectorBuilder)

    def setUp(self):
        super(JenkinsTestCollectorBuildStepTest, self).setUp()
        self.old_config = deepcopy(current_app.config)
        current_app.config['CHANGES_CLIENT_BUILD_TYPES']['legacy_2'] = {
            'uses_client': False}

    def tearDown(self):
        current_app.config = self.old_config
        super(JenkinsTestCollectorBuildStepTest, self).tearDown()

    def test_get_builder(self):
        builder = self.get_buildstep().get_builder()
        assert builder.job_name == 'foo-bar'
        assert builder.script == 'exit 0'
        assert builder.cluster == 'default'

    def test_collection_build_type(self):
        step = self.get_buildstep()
        builder = step.get_builder()

        assert step.build_type == 'legacy'
        assert builder.build_type == 'legacy'

    def test_shard_build_type(self):
        step = self.get_buildstep()
        builder = step.get_builder(build_type=step.shard_build_type)

        assert step.shard_build_type == 'legacy_2'
        assert builder.build_type == 'legacy_2'

    @mock.patch.object(JenkinsTestCollectorBuildStep, 'get_builder')
    def test_default_artifact_handling(self, get_builder):
        builder = self.get_mock_builder()
        builder.get_required_handler.return_value = TestsJsonHandler
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

    def test_validate_shards(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build, data={
            'job_name': 'server',
            'build_no': '35',
        })

        buildstep = self.get_buildstep()

        # Non-expanded phase
        phase = self.create_jobphase(job, label='collect')
        step = self.create_jobstep(phase, data={
            'item_id': 13,
            'job_name': 'server',
        })

        assert buildstep._validate_shards([step]) == Result.passed

        # Expanded phase
        phase2 = self.create_jobphase(job, label='run tests')
        step2_1 = self.create_jobstep(phase2, data={
            'expanded': True,
            'shard_count': 2,
            'item_id': 13,
            'job_name': 'foo-bar',
        })
        step2_2 = self.create_jobstep(phase2, data={
            'expanded': True,
            'shard_count': 2,
            'item_id': 13,
            'job_name': 'foo-bar',
        })

        assert buildstep._validate_shards([step2_1]) == Result.unknown
        assert buildstep._validate_shards([step2_1, step2_2]) == Result.passed

    def test_validate_phase(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build, data={
            'job_name': 'server',
            'build_no': '35',
        })

        # Non-expanded phase
        phase = self.create_jobphase(job, label='collect')
        step = self.create_jobstep(phase, data={
            'item_id': 13,
            'job_name': 'server',
        })
        step.result = Result.passed

        buildstep = self.get_buildstep()
        buildstep.validate_phase(phase)
        assert phase.result == Result.passed

        # Expanded phase
        phase2 = self.create_jobphase(job, label='run tests')
        step2_1 = self.create_jobstep(phase2, data={
            'expanded': True,
            'shard_count': 2,
            'item_id': 13,
            'job_name': 'foo-bar',
        })
        step2_2 = self.create_jobstep(phase2, data={
            'expanded': True,
            'shard_count': 2,
            'item_id': 13,
            'job_name': 'foo-bar',
        })
        step2_1.result = Result.passed
        step2_2.result = Result.passed

        buildstep = self.get_buildstep()
        buildstep.validate_phase(phase2)
        assert phase2.result == Result.passed

        # Expanded phase with missing step
        phase3 = self.create_jobphase(job, label='run tests 2')
        step3_1 = self.create_jobstep(phase3, data={
            'expanded': True,
            'shard_count': 2,
            'item_id': 13,
            'job_name': 'foo-bar',
        })
        step3_1.result = Result.passed

        buildstep = self.get_buildstep()
        buildstep.validate_phase(phase3)
        assert phase3.result == Result.unknown

        # Expanded phase with failing step
        phase4 = self.create_jobphase(job, label='run tests 3')
        step4_1 = self.create_jobstep(phase4, data={
            'expanded': True,
            'shard_count': 2,
            'item_id': 13,
            'job_name': 'foo-bar',
        })
        step4_2 = self.create_jobstep(phase4, data={
            'expanded': True,
            'shard_count': 2,
            'item_id': 13,
            'job_name': 'foo-bar',
        })
        step4_1.result = Result.passed
        step4_2.result = Result.failed

        buildstep = self.get_buildstep()
        buildstep.validate_phase(phase4)
        assert phase4.result == Result.failed

        # Expanded phase with replaced step
        phase5 = self.create_jobphase(job, label='run tests 4')
        step5_1 = self.create_jobstep(phase5, data={
            'expanded': True,
            'shard_count': 2,
            'item_id': 13,
            'job_name': 'foo-bar',
        })
        step5_2 = self.create_jobstep(phase5, data={
            'expanded': True,
            'shard_count': 2,
            'item_id': 13,
            'job_name': 'foo-bar',
        })
        step5_3 = self.create_jobstep(phase5, data={
            'expanded': True,
            'shard_count': 2,
            'item_id': 13,
            'job_name': 'foo-bar',
        })

        step5_1.result = Result.passed
        step5_2.result = Result.infra_failed
        step5_3.result = Result.passed
        step5_2.replacement_id = step5_3.id

        buildstep = self.get_buildstep()
        buildstep.validate_phase(phase5)
        assert phase5.result == Result.passed

    @responses.activate
    @mock.patch.object(JenkinsTestCollectorBuilder, 'fetch_artifact')
    @mock.patch.object(JenkinsTestCollectorBuilder, 'create_jenkins_job_from_params')
    @mock.patch.object(JenkinsTestCollectorBuilder, 'get_job_parameters')
    @mock.patch.object(TestsExpander, 'get_test_stats')
    @mock.patch('changes.backends.jenkins.builder.ArtifactStoreClient', ArtifactStoreMock)
    def test_job_expansion(self, get_test_stats, get_job_parameters,
                           create_jenkins_job_from_params, fetch_artifact):
        """
        Fairly heavy integration test which mocks out a few things but ensures
        that generic APIs are called correctly and the tests.json is parsed
        as expected.
        """
        fetch_artifact.return_value.content = json.dumps({
            'phase': 'Test',
            'cmd': 'py.test --junit=junit.xml {test_names}',
            'tests': [
                'foo/bar.py',
                'foo/baz.py',
                'foo.bar.test_biz',
                'foo.bar.test_buz',
            ],
        })
        create_jenkins_job_from_params.return_value = {
            'job_name': 'foo-bar',
            'build_no': 23,
        }

        get_job_parameters.return_value = {'PARAM': '44'}

        get_test_stats.return_value = {
            ('foo', 'bar'): 50,
            ('foo', 'baz'): 15,
            ('foo', 'bar', 'test_biz'): 10,
            ('foo', 'bar', 'test_buz'): 200,
        }, 68

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
            name='tests.json',
            data={'fileName': 'tests.json'},
        )

        buildstep = self.get_buildstep()
        with mock.patch.object(JobPlan, 'get_build_step_for_job') as get_build_step_for_job:
            get_build_step_for_job.return_value = (None, buildstep)
            buildstep.fetch_artifact(artifact)

        phase2 = JobPhase.query.filter(
            JobPhase.job_id == job.id,
            JobPhase.id != phase.id,
        ).first()

        assert phase2, "phase wasn't created"
        assert phase2.label == 'Test'
        assert phase2.status == Status.queued

        new_steps = sorted(phase2.current_steps, key=lambda x: x.data['weight'], reverse=True)

        assert len(new_steps) == 2
        assert new_steps[0].data['expanded'] is True
        assert new_steps[0].data['build_no'] == 23
        assert new_steps[0].data['job_name'] == 'foo-bar'
        assert new_steps[0].data['tests'] == ['foo.bar.test_buz']
        assert new_steps[0].data['path'] == ''
        assert new_steps[0].data['cmd'] == 'py.test --junit=junit.xml {test_names}'
        assert new_steps[0].data['weight'] == 201

        assert new_steps[1].data['expanded'] is True
        assert new_steps[1].data['build_no'] == 23
        assert new_steps[1].data['job_name'] == 'foo-bar'
        assert new_steps[1].data['tests'] == [
            'foo/bar.py',
            'foo/baz.py',
            'foo.bar.test_biz',
        ]
        assert new_steps[1].data['path'] == ''
        assert new_steps[1].data['cmd'] == 'py.test --junit=junit.xml {test_names}'
        assert new_steps[1].data['weight'] == 78

        fetch_artifact.assert_called_once_with(artifact.step, artifact.data)
        get_job_parameters.assert_any_call(
            job,
            changes_bid=new_steps[0].id.hex,
            script='py.test --junit=junit.xml foo.bar.test_buz',
            path='',
            setup_script='',
            teardown_script='',
        )
        create_jenkins_job_from_params.assert_any_call(
            job_name='foo-bar',
            changes_bid=new_steps[0].id.hex,
            is_diff=False,
            params=[{'name': 'PARAM', 'value': '44'}],
        )
        get_job_parameters.assert_any_call(
            job,
            changes_bid=new_steps[1].id.hex,
            script='py.test --junit=junit.xml foo/bar.py foo/baz.py foo.bar.test_biz',
            path='',
            setup_script='',
            teardown_script='',
        )
        create_jenkins_job_from_params.assert_any_call(
            job_name='foo-bar',
            changes_bid=new_steps[1].id.hex,
            is_diff=False,
            params=[{'name': 'PARAM', 'value': '44'}],
        )

        # If fetch_artifact() is called again with different weights so
        # that it divvies up the tests differently, does a broken
        # double-shard build result?

        get_test_stats.return_value = {
            ('foo', 'bar'): 50,
            ('foo', 'baz'): 15,
            ('foo', 'bar', 'test_biz'): 10,
            ('foo', 'bar', 'test_buz'): 55,
        }, 68

        buildstep.fetch_artifact(artifact)

        all_steps = phase2.current_steps
        assert len(all_steps) == 2

    @responses.activate
    @mock.patch.object(JenkinsTestCollectorBuilder, 'fetch_artifact')
    @mock.patch.object(JenkinsTestCollectorBuilder, 'create_jenkins_job_from_params')
    @mock.patch.object(JenkinsTestCollectorBuilder, 'get_job_parameters')
    @mock.patch.object(TestsExpander, 'get_test_stats')
    @mock.patch('changes.backends.jenkins.builder.ArtifactStoreClient', ArtifactStoreMock)
    def test_create_replacement_jobstep(self, get_test_stats, get_job_parameters,
                                        create_jenkins_job_from_params, fetch_artifact):
        """
        Tests create_replacement_jobstep by running a very similar test to
        test_job_expansion, failing one of the jobsteps and then replacing it,
        and making sure the results still end up the same.
        """
        fetch_artifact.return_value.content = json.dumps({
            'phase': 'Test',
            'cmd': 'py.test --junit=junit.xml {test_names}',
            'tests': [
                'foo/bar.py',
                'foo/baz.py',
                'foo.bar.test_biz',
                'foo.bar.test_buz',
            ],
        })
        create_jenkins_job_from_params.return_value = {
            'job_name': 'foo-bar',
            'build_no': 23,
        }

        get_job_parameters.return_value = {'PARAM': '44'}

        get_test_stats.return_value = {
            ('foo', 'bar'): 50,
            ('foo', 'baz'): 15,
            ('foo', 'bar', 'test_biz'): 10,
            ('foo', 'bar', 'test_buz'): 200,
        }, 68

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
            name='tests.json',
            data={'fileName': 'tests.json'},
        )

        buildstep = self.get_buildstep()
        with mock.patch.object(JobPlan, 'get_build_step_for_job') as get_build_step_for_job:
            get_build_step_for_job.return_value = (None, buildstep)
            buildstep.fetch_artifact(artifact)

        phase2 = JobPhase.query.filter(
            JobPhase.job_id == job.id,
            JobPhase.id != phase.id,
        ).first()
        assert phase2, "phase wasn't created"

        new_steps = sorted(phase2.current_steps, key=lambda x: x.data['weight'], reverse=True)

        failstep = new_steps[0]
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
        new_steps = sorted(phase2.current_steps, key=lambda x: x.data['weight'], reverse=True)
        assert new_steps[0] == replacement_step

        assert len(new_steps) == 2
        assert new_steps[0].data['expanded'] is True
        assert new_steps[0].data['build_no'] == 23
        assert new_steps[0].data['job_name'] == 'foo-bar'
        assert new_steps[0].data['tests'] == ['foo.bar.test_buz']
        assert new_steps[0].data['path'] == ''
        assert new_steps[0].data['cmd'] == 'py.test --junit=junit.xml {test_names}'
        assert new_steps[0].data['weight'] == 201

        assert new_steps[1].data['expanded'] is True
        assert new_steps[1].data['build_no'] == 23
        assert new_steps[1].data['job_name'] == 'foo-bar'
        assert new_steps[1].data['tests'] == [
            'foo/bar.py',
            'foo/baz.py',
            'foo.bar.test_biz',
        ]
        assert new_steps[1].data['path'] == ''
        assert new_steps[1].data['cmd'] == 'py.test --junit=junit.xml {test_names}'
        assert new_steps[1].data['weight'] == 78

        fetch_artifact.assert_called_once_with(artifact.step, artifact.data)
        get_job_parameters.assert_any_call(
            job,
            changes_bid=new_steps[0].id.hex,
            script='py.test --junit=junit.xml foo.bar.test_buz',
            path='',
            setup_script='',
            teardown_script='',
        )
        create_jenkins_job_from_params.assert_any_call(
            job_name='foo-bar',
            changes_bid=new_steps[0].id.hex,
            is_diff=False,
            params=[{'name': 'PARAM', 'value': '44'}],
        )
        get_job_parameters.assert_any_call(
            job,
            changes_bid=new_steps[1].id.hex,
            script='py.test --junit=junit.xml foo/bar.py foo/baz.py foo.bar.test_biz',
            path='',
            setup_script='',
            teardown_script='',
        )
        create_jenkins_job_from_params.assert_any_call(
            job_name='foo-bar',
            changes_bid=new_steps[1].id.hex,
            is_diff=False,
            params=[{'name': 'PARAM', 'value': '44'}],
        )

        # If fetch_artifact() is called again with different weights so
        # that it divvies up the tests differently, does a broken
        # double-shard build result?

        get_test_stats.return_value = {
            ('foo', 'bar'): 50,
            ('foo', 'baz'): 15,
            ('foo', 'bar', 'test_biz'): 10,
            ('foo', 'bar', 'test_buz'): 55,
        }, 68

        buildstep.fetch_artifact(artifact)

        all_steps = phase2.current_steps
        assert len(all_steps) == 2

    @responses.activate
    @mock.patch.object(JenkinsTestCollectorBuilder, 'fetch_artifact')
    @mock.patch.object(JenkinsTestCollectorBuilder, 'create_jenkins_job_from_params')
    @mock.patch.object(JenkinsTestCollectorBuilder, 'get_job_parameters')
    @mock.patch.object(TestsExpander, 'get_test_stats')
    @mock.patch('changes.backends.jenkins.builder.ArtifactStoreClient', ArtifactStoreMock)
    def test_job_expansion_no_tests(self, get_test_stats, get_job_parameters,
                           create_jenkins_job_from_params, fetch_artifact):
        fetch_artifact.return_value.content = json.dumps({
            'phase': 'Test',
            'cmd': 'py.test --junit=junit.xml {test_names}',
            'tests': [],
        })
        create_jenkins_job_from_params.return_value = {
            'job_name': 'foo-bar',
            'build_no': 23,
        }

        get_test_stats.return_value = {
            ('foo', 'bar'): 50,
            ('foo', 'baz'): 15,
        }, 68

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
            name='tests.json',
            data={'fileName': 'tests.json'},
        )

        buildstep = self.get_buildstep()
        with mock.patch.object(JobPlan, 'get_build_step_for_job') as get_build_step_for_job:
            get_build_step_for_job.return_value = (None, buildstep)
            buildstep.fetch_artifact(artifact)

        phase2 = JobPhase.query.filter(
            JobPhase.job_id == job.id,
            JobPhase.id != phase.id,
        ).first()
        assert phase2, "phase wasn't created"
        assert phase2.status == Status.finished
        assert phase2.result == Result.passed

        new_steps = JobStep.query.filter(
            JobStep.phase_id == phase2.id
        )
        assert len(list(new_steps)) == 0
