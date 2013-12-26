from __future__ import absolute_import

import mock

from changes.backends.jenkins.builder import JenkinsBuilder
from changes.backends.jenkins.buildstep import JenkinsBuildStep
from changes.config import db
from changes.models import RemoteEntity
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
    def test_create_job(self, get_builder):
        builder = mock.Mock()
        get_builder.return_value = builder

        job = self.create_job(self.project)

        buildstep = self.get_buildstep()
        buildstep.execute(job)

        builder.create_job.assert_called_once_with(job)

    @mock.patch.object(JenkinsBuildStep, 'get_builder')
    def test_sync_job(self, get_builder):
        builder = mock.Mock()
        get_builder.return_value = builder

        job = self.create_job(self.project, data={
            'job_name': 'server',
            'build_no': '35',
        })

        buildstep = self.get_buildstep()
        buildstep.execute(job)

        builder.sync_job.assert_called_once_with(job)

    @mock.patch.object(JenkinsBuildStep, 'get_builder')
    def test_legacy_sync_job(self, get_builder):
        builder = mock.Mock()
        get_builder.return_value = builder

        job = self.create_job(self.project)

        entity = RemoteEntity(
            provider='jenkins',
            remote_id='a' * 40,
            internal_id=job.id.hex,
            type='build',
            data={
                'job_name': 'server',
                'build_no': '35',
            },
        )
        db.session.add(entity)

        buildstep = self.get_buildstep()
        buildstep.execute(job)

        builder.sync_job.assert_called_once_with(job)
