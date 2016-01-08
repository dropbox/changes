from __future__ import absolute_import

from flask import current_app

import mock

from copy import deepcopy
from pytest import raises
from uuid import uuid4

from changes.backends.jenkins.generic_builder import JenkinsGenericBuilder
from changes.config import db
from changes.buildsteps.base import LXCConfig

from .test_builder import BaseTestCase


class JenkinsGenericBuilderTest(BaseTestCase):
    builder_cls = JenkinsGenericBuilder
    builder_options = {
        'master_urls': ['http://jenkins.example.com'],
        'job_name': 'server',
        'setup_script': 'setup',
        'script': 'py.test',
        'teardown_script': 'teardown',
        'cluster': 'default',
        'build_type': 'test_harness'
    }

    def setUp(self):
        super(JenkinsGenericBuilderTest, self).setUp()
        self.old_config = deepcopy(current_app.config)
        current_app.config['LXC_RELEASE'] = 'release'
        current_app.config['CHANGES_CLIENT_BUILD_TYPES']['test_harness'] = {
            'uses_client': True,
            'adapter': 'basic',
            'jenkins-command': 'command',
            'commands': [
                {'script': 'script1'},
                {'script': 'script2'}
            ]
        }
        current_app.config['CHANGES_CLIENT_BUILD_TYPES']['test_harness_2'] = {
            'use_client': True,
            'adapter': 'basic',
            'jenkins-command': 'command',
            'can_snapshot': True,
            'commands': [
                {'script': 'script1'},
                {'script': 'script2'}
            ]
        }
        current_app.config['CHANGES_CLIENT_BUILD_TYPES']['test_harness_invalid_1'] = {
            'uses_client': True,
            'jenkins-command': 'command',
            'commands': [
                {'script': 'script1'},
                {'script': 'script2'}
            ]
        }
        current_app.config['CHANGES_CLIENT_BUILD_TYPES']['test_harness_invalid_2'] = {
            'uses_client': True,
            'adapter': 'basic',
            'commands': [
                {'script': 'script1'},
                {'script': 'script2'}
            ]
        }

    def tearDown(self):
        current_app.config = self.old_config
        super(JenkinsGenericBuilderTest, self).tearDown()

    def test_get_job_parameters(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)

        builder = self.get_builder()
        assert builder.build_type == 'test_harness'

        changes_bid = '5a9d18bb87ff12835dc844883c5c3ebe'  # arbitrary

        result = builder.get_job_parameters(job, changes_bid, path='foo')
        assert result['CHANGES_BID'] == changes_bid
        assert result['CHANGES_PID'] == job.project.slug
        assert result['PROJECT_CONFIG'] == job.project.get_config_path()
        assert result['REPO_URL'] == job.project.repository.url
        assert result['REPO_VCS'] == job.project.repository.backend.name
        assert result['REVISION'] == job.source.revision_sha
        assert result['SETUP_SCRIPT'] == self.builder_options['setup_script']
        assert result['SCRIPT'] == self.builder_options['script']
        assert result['TEARDOWN_SCRIPT'] == self.builder_options['teardown_script']
        assert result['CLUSTER'] == self.builder_options['cluster']
        assert result['WORK_PATH'] == 'foo'
        assert result['PHAB_REVISION_ID'] == '1234'
        assert result['PHAB_DIFF_ID'] == '54321'

        # magic number that is simply the current number of parameters. Ensures that
        # there is nothing "extra"
        assert len(result) == 24

        # test defaulting for lxc
        # pre/post are defined in conftest.py
        assert result['CHANGES_CLIENT_LXC_PRE_LAUNCH'] == 'echo pre'
        assert result['CHANGES_CLIENT_LXC_POST_LAUNCH'] == 'echo post'
        assert result['CHANGES_CLIENT_LXC_RELEASE'] == 'release'

        # test optional values
        result = builder.get_job_parameters(job, uuid4().hex)
        assert result['WORK_PATH'] == ''
        assert result['C_WORKSPACE'] == ''
        assert result['RESET_SCRIPT'] == ''

    def test_create_commands(self):
        artifacts = ['coverage.xml', 'junit.xml']
        builder = self.get_builder(artifacts=artifacts)
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)

        params = builder.get_job_parameters(job, jobstep.id.hex, path='foo')
        builder.create_commands(jobstep, params)
        db.session.commit()

        assert len(jobstep.commands) == 2
        assert jobstep.commands[0].script == 'script1'
        assert jobstep.commands[1].script == 'script2'
        assert jobstep.commands[0].env == jobstep.commands[1].env
        assert jobstep.commands[0].env['SCRIPT'] == 'py.test'
        assert jobstep.commands[0].artifacts == artifacts

    def test_commands_snapshot(self):
        builder = self.get_builder()
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)
        plan = self.create_plan(project)
        self.create_job_plan(job, plan)
        snapshot = self.create_snapshot(project)
        self.create_snapshot_image(snapshot, plan, job=job)

        params = builder.get_job_parameters(job, jobstep.id.hex, path='foo')
        assert params['SETUP_SCRIPT'] == self.builder_options['setup_script']
        assert params['SCRIPT'] == ':'
        assert params['TEARDOWN_SCRIPT'] == self.builder_options['teardown_script']

        builder.create_commands(jobstep, params)
        db.session.commit()

        for command in jobstep.commands:
            assert command.env['SETUP_SCRIPT'] == self.builder_options['setup_script']
            assert command.env['SCRIPT'] == ':'
            assert command.env['TEARDOWN_SCRIPT'] == self.builder_options['teardown_script']

    @mock.patch.object(JenkinsGenericBuilder, 'artifacts_for_jobstep')
    def test_artifacts_for_jobstep(self, artifacts_for_jobstep):
        artifacts = ['tests.json']
        artifacts_for_jobstep.return_value = artifacts
        builder = self.get_builder(artifacts=['coverage.xml'])
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)

        params = builder.get_job_parameters(job, jobstep.id.hex, path='foo')
        builder.create_commands(jobstep, params)
        db.session.commit()

        assert len(jobstep.commands) == 2
        assert jobstep.commands[0].artifacts == artifacts

    def test_commands_snapshot_with_script(self):
        """Test that we replace script with snapshot_script when
        running a snapshot build, if snapshot_script is not None.
        """
        builder = self.get_builder(snapshot_script='cache-data')
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)
        plan = self.create_plan(project)
        self.create_job_plan(job, plan)
        snapshot = self.create_snapshot(project)
        self.create_snapshot_image(snapshot, plan, job=job)

        params = builder.get_job_parameters(job, jobstep.id.hex, path='foo')
        assert params['SCRIPT'] == 'cache-data'

        builder.create_commands(jobstep, params)
        db.session.commit()

        for command in jobstep.commands:
            assert command.env['SCRIPT'] == 'cache-data'

    def test_can_snapshot(self):
        assert not self.get_builder().can_snapshot()
        assert self.get_builder(build_type="test_harness_2").can_snapshot()

    def test_get_job_parameters_with_reset_script(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)

        builder = self.get_builder(reset_script='reset_me.sh')

        result = builder.get_job_parameters(job, uuid4().hex, path='foo')
        assert result['RESET_SCRIPT'] == 'reset_me.sh'

    def validate_build_type(self, build_type):
        builder = self.get_builder()
        build_desc = current_app.config['CHANGES_CLIENT_BUILD_TYPES'][build_type]
        builder.validate_build_desc(build_type, build_desc)

    def test_valid_build_desc(self):
        self.validate_build_type("test_harness")

    def test_invalid_build_desc_missing_adapter(self):
        with raises(ValueError):
            self.validate_build_type("test_harness_invalid_1")

    def test_invalid_build_desc_missing_jcommand(self):
        with raises(ValueError):
            self.validate_build_type("test_harness_invalid_2")

    def test_get_expected_image_none(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)

        builder = self.get_builder()
        assert builder.get_expected_image(job.id) is None

    def test_get_expected_image(self):
        project = self.create_project()
        build = self.create_build(project)
        plan = self.create_plan(project)
        snapshot = self.create_snapshot(project)
        job = self.create_job(build)
        snapshot_image = self.create_snapshot_image(snapshot, plan, job=job)
        self.create_job_plan(job, plan)

        db.session.commit()
        builder = self.get_builder()
        assert builder.get_expected_image(job.id) == snapshot_image.id

    def test_get_lxc_config_legacy(self):
        current_app.config['CHANGES_CLIENT_BUILD_TYPES']['legacy'] = {
            'uses_client': False,
        }
        builder = self.get_builder(build_type='legacy')
        jobstep = mock.Mock()
        jobstep.job_id = uuid4()
        assert builder.get_lxc_config(jobstep=jobstep) is None

    def test_get_lxc_config_basic(self):
        current_app.config['CHANGES_CLIENT_BUILD_TYPES']['basic999'] = {
            'uses_client': True,
            'adapter': 'basic',
            'jenkins-command': 'command',
            'commands': [
                {'script': 'script1'},
                {'script': 'script2'}
            ]
        }
        builder = self.get_builder(build_type='basic999')
        jobstep = mock.Mock()
        jobstep.job_id = uuid4()
        assert builder.get_lxc_config(jobstep=jobstep) is None

    def test_get_lxc_config_lxc(self):
        current_app.config['CHANGES_CLIENT_BUILD_TYPES']['lxc_test'] = {
            'uses_client': True,
            'adapter': 'lxc',
            'pre-launch': 'pre.sh',
            'post-launch': 'post.sh',
            'release': 'squishy',
            'jenkins-command': 'command',
            'commands': [
                {'script': 'script1'},
            ]
        }
        bucket = 'S3BUCKET'
        current_app.config['SNAPSHOT_S3_BUCKET'] = bucket

        builder = self.get_builder(build_type='lxc_test')
        jobstep = mock.Mock()
        jobstep.job_id = uuid4()
        lxc_config = builder.get_lxc_config(jobstep=jobstep)
        assert lxc_config == LXCConfig(compression='lz4',
                                       s3_bucket=bucket,
                                       prelaunch='pre.sh',
                                       postlaunch='post.sh',
                                       release='squishy')

    def test_get_lxc_config_lxc_defaults(self):
        # Defaults from the app config rather than values from the build_type.
        current_app.config['CHANGES_CLIENT_BUILD_TYPES']['lxc_test'] = {
            'uses_client': True,
            'adapter': 'lxc',
            'jenkins-command': 'command',
            'commands': [
                {'script': 'script1'},
            ]
        }
        bucket = 'S3BUCKET'
        current_app.config['SNAPSHOT_S3_BUCKET'] = bucket
        current_app.config['LXC_PRE_LAUNCH'] = 'default-pre.sh'
        current_app.config['LXC_POST_LAUNCH'] = 'default-post.sh'
        current_app.config['LXC_RELEASE'] = 'default release'

        builder = self.get_builder(build_type='lxc_test')
        jobstep = mock.Mock()
        jobstep.job_id = uuid4()
        lxc_config = builder.get_lxc_config(jobstep=jobstep)
        assert lxc_config == LXCConfig(compression='lz4',
                                       s3_bucket=bucket,
                                       prelaunch='default-pre.sh',
                                       postlaunch='default-post.sh',
                                       release='default release')
