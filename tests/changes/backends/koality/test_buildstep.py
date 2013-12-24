from __future__ import absolute_import

import mock

from changes.backends.koality.builder import KoalityBuilder
from changes.backends.koality.buildstep import KoalityBuildStep
from changes.testutils import TestCase


class KoalityBuildStepTest(TestCase):
    def get_buildstep(self):
        return KoalityBuildStep(project_id=26)

    def test_get_builder(self):
        buildstep = self.get_buildstep()
        builder = buildstep.get_builder()
        assert builder.project_id == 26
        assert type(builder) == KoalityBuilder

    @mock.patch.object(KoalityBuildStep, 'get_builder')
    def test_execute(self, get_builder):
        builder = mock.Mock()
        get_builder.return_value = builder

        build = self.create_build(self.project)

        buildstep = self.get_buildstep()
        buildstep.execute(build)

        builder.create_build.assert_called_once_with(build)
