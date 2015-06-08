from __future__ import absolute_import

from flask import current_app

from uuid import uuid4

from changes.backends.jenkins.generic_builder import JenkinsGenericBuilder
from changes.config import db
from .test_builder import BaseTestCase


class JenkinsGenericBuilderTest(BaseTestCase):
    builder_cls = JenkinsGenericBuilder
    builder_options = {
        'master_urls': ['http://jenkins.example.com'],
        'job_name': 'server',
        'script': 'py.test',
        'cluster': 'default',
        'diff_cluster': 'diff_cluster',
        'build_type': 'test_harness'
    }

    def setUp(self):
        super(JenkinsGenericBuilderTest, self).setUp()
        current_app.config['CHANGES_CLIENT_BUILD_TYPES']['test_harness'] = {
            'use_client': True,
            'adapter': 'basic',
            'jenkins-command': 'command',
            'commands': [
                {'script': 'script1'},
                {'script': 'script2'}
            ]
        }

    def tearDown(self):
        current_app.config['CHANGES_CLIENT_BUILD_TYPES'].pop('test_harness', None)
        super(JenkinsGenericBuilderTest, self).tearDown()

    def test_get_job_parameters(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)

        builder = self.get_builder()
        changes_bid = '5a9d18bb87ff12835dc844883c5c3ebe'  # arbitrary

        result = builder.get_job_parameters(job, changes_bid, path='foo')
        assert {'name': 'CHANGES_BID', 'value': changes_bid} in result
        assert {'name': 'CHANGES_PID', 'value': job.project.slug} in result
        assert {'name': 'REPO_URL', 'value': job.project.repository.url} in result
        assert {'name': 'REPO_VCS', 'value': job.project.repository.backend.name} in result
        assert {'name': 'REVISION', 'value': job.source.revision_sha} in result
        assert {'name': 'SCRIPT', 'value': self.builder_options['script']} in result
        assert {'name': 'CLUSTER', 'value': self.builder_options['cluster']} in result
        assert {'name': 'WORK_PATH', 'value': 'foo'} in result
        assert len(result) == 10

        # test optional values
        result = builder.get_job_parameters(job, uuid4().hex)
        assert {'name': 'WORK_PATH', 'value': ''} in result
        assert {'name': 'C_WORKSPACE', 'value': ''} in result
        assert {'name': 'RESET_SCRIPT', 'value': ''} in result

    def test_commands(self):
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
