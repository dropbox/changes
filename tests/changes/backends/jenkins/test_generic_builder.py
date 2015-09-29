from __future__ import absolute_import

from flask import current_app

from copy import deepcopy
from pytest import raises
from uuid import uuid4

from changes.backends.jenkins.generic_builder import JenkinsGenericBuilder
from changes.config import db
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
        'diff_cluster': 'diff_cluster',
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
        assert {'name': 'CHANGES_BID', 'value': changes_bid} in result
        assert {'name': 'CHANGES_PID', 'value': job.project.slug} in result
        assert {'name': 'REPO_URL', 'value': job.project.repository.url} in result
        assert {'name': 'REPO_VCS', 'value': job.project.repository.backend.name} in result
        assert {'name': 'REVISION', 'value': job.source.revision_sha} in result
        assert {'name': 'SETUP_SCRIPT', 'value': self.builder_options['setup_script']} in result
        assert {'name': 'SCRIPT', 'value': self.builder_options['script']} in result
        assert {'name': 'TEARDOWN_SCRIPT', 'value': self.builder_options['teardown_script']} in result
        assert {'name': 'CLUSTER', 'value': self.builder_options['cluster']} in result
        assert {'name': 'WORK_PATH', 'value': 'foo'} in result

        # magic number that is simply the current number of parameters. Ensures that
        # there is nothing "extra"
        assert len(result) == 21

        # test defaulting for lxc
        # pre/post are defined in conftest.py
        assert {'name': 'CHANGES_CLIENT_LXC_PRE_LAUNCH', 'value': 'echo pre'} in result
        assert {'name': 'CHANGES_CLIENT_LXC_POST_LAUNCH', 'value': 'echo post'} in result
        assert {'name': 'CHANGES_CLIENT_LXC_RELEASE', 'value': 'release'} in result

        # test optional values
        result = builder.get_job_parameters(job, uuid4().hex)
        assert {'name': 'WORK_PATH', 'value': ''} in result
        assert {'name': 'C_WORKSPACE', 'value': ''} in result
        assert {'name': 'RESET_SCRIPT', 'value': ''} in result

    def test_create_commands(self):
        builder = self.get_builder()
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
        snapshot_image = self.create_snapshot_image(snapshot, plan, job=job)

        params = builder.get_job_parameters(job, jobstep.id.hex, path='foo')
        assert {'name': 'SETUP_SCRIPT', 'value': self.builder_options['setup_script']} in params
        assert {'name': 'SCRIPT', 'value': ':'} in params
        assert {'name': 'TEARDOWN_SCRIPT', 'value': self.builder_options['teardown_script']} in params

        builder.create_commands(jobstep, params)
        db.session.commit()

        for command in jobstep.commands:
            assert command.env['SETUP_SCRIPT'] == self.builder_options['setup_script']
            assert command.env['SCRIPT'] == ':'
            assert command.env['TEARDOWN_SCRIPT'] == self.builder_options['teardown_script']

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
        snapshot_image = self.create_snapshot_image(snapshot, plan, job=job)

        params = builder.get_job_parameters(job, jobstep.id.hex, path='foo')
        assert {'name': 'SCRIPT', 'value': 'cache-data'} in params

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
        assert {'name': 'RESET_SCRIPT', 'value': 'reset_me.sh'} in result

    def test_get_job_parameters_diff(self):
        project = self.create_project()
        patch = self.create_patch()
        source = self.create_source(project, patch=patch)
        build = self.create_build(project, source=source)
        job = self.create_job(build)

        builder = self.get_builder()

        result = builder.get_job_parameters(job, uuid4().hex, path='foo')
        assert {'name': 'CLUSTER', 'value': self.builder_options['diff_cluster']} in result

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
