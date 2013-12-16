from __future__ import absolute_import

import mock

from changes.backends.jenkins.builder import JenkinsBuilder
from changes.backends.jenkins.buildstep import JenkinsBuildStep
from changes.testutils import TestCase


class JenkinsBuildStepTest(TestCase):
    def get_buildstep(self):
        return JenkinsBuildStep()

    def test_get_builder(self):
        buildstep = self.get_buildstep()
        builder = buildstep.get_builder()
        assert type(builder) == JenkinsBuilder

    @mock.patch.object(JenkinsBuildStep, 'get_builder')
    def test_execute(self, get_builder):
        builder = mock.Mock()
        get_builder.return_value = builder

        build = self.create_build(self.project)

        buildstep = self.get_buildstep()
        buildstep.execute(build)

        builder.create_build.assert_called_once_with(build)

    @mock.patch.object(JenkinsBuildStep, 'get_builder')
    def test_sync(self, get_builder):
        builder = mock.Mock()
        get_builder.return_value = builder

        build = self.create_build(self.project)

        buildstep = self.get_buildstep()
        buildstep.sync(build)

        builder.sync_build.assert_called_once_with(build)
