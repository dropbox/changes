from __future__ import absolute_import

from changes.backends.jenkins.generic_builder import JenkinsGenericBuilder
from .test_builder import BaseTestCase


class JenkinsGenericBuilderTest(BaseTestCase):
    builder_cls = JenkinsGenericBuilder
    builder_options = {
        'master_urls': ['http://jenkins.example.com'],
        'job_name': 'server',
        'script': 'py.test',
        'cluster': 'default',
    }

    def test_get_job_parameters(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)

        builder = self.get_builder()

        result = builder.get_job_parameters(job, path='foo')
        assert {'name': 'CHANGES_BID', 'value': job.id.hex} in result
        assert {'name': 'CHANGES_PID', 'value': job.project.slug} in result
        assert {'name': 'REPO_URL', 'value': job.project.repository.url} in result
        assert {'name': 'REPO_VCS', 'value': job.project.repository.backend.name} in result
        assert {'name': 'REVISION', 'value': job.source.revision_sha} in result
        assert {'name': 'SCRIPT', 'value': self.builder_options['script']} in result
        assert {'name': 'CLUSTER', 'value': self.builder_options['cluster']} in result
        assert {'name': 'WORK_PATH', 'value': 'foo'} in result
        assert len(result) == 9

        # test optional values
        result = builder.get_job_parameters(job)
        assert {'name': 'WORK_PATH', 'value': ''} in result
        assert {'name': 'C_WORKSPACE', 'value': ''} in result
