from __future__ import absolute_import, print_function

from cStringIO import StringIO

import mock

from changes.artifacts.base import ArtifactHandler
from changes.artifacts.manager import Manager
from changes.testutils import TestCase


class ManagerTest(TestCase):
    @mock.patch.object(ArtifactHandler, 'process')
    def test_process_behavior(self, process):
        class _CovHandler(ArtifactHandler):
            FILENAMES = ('coverage.xml',)

        class _OtherHandler(ArtifactHandler):
            FILENAMES = ('/other.xml',)

        manager = Manager([_CovHandler, _OtherHandler])

        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)

        artifact = self.create_artifact(
            step=jobstep,
            name='junit.xml',
        )
        artifact.file.save(StringIO(), artifact.name)
        manager.process(artifact)

        assert not process.called

        artifact = self.create_artifact(
            step=jobstep,
            name='coverage.xml',
        )
        artifact.file.save(StringIO(), artifact.name)
        manager.process(artifact)

        artifact = self.create_artifact(
            step=jobstep,
            name='foo/coverage.xml',
        )
        artifact.file.save(StringIO(), artifact.name)
        manager.process(artifact)

        assert process.call_count == 2

        artifact = self.create_artifact(
            step=jobstep,
            name='artifactstore/other.xml'
        )
        artifact.file.save(StringIO(), artifact.name)
        manager.process(artifact)

        assert process.call_count == 3

        # shouldn't process this
        artifact = self.create_artifact(
            step=jobstep,
            name='artifactstore/foo/other.xml'
        )
        artifact.file.save(StringIO(), artifact.name)
        manager.process(artifact)

        assert process.call_count == 3

    def test_can_process(self):
        class _CovHandler(ArtifactHandler):
            FILENAMES = ('coverage.xml',)

        class _OtherHandler(ArtifactHandler):
            FILENAMES = ('/other.xml', 'foo/*/weird.json')

        manager = Manager([_CovHandler, _OtherHandler])

        assert manager.can_process('foo/coverage.xml')
        assert manager.can_process('other.xml')
        assert manager.can_process('artifactstore/other.xml')
        assert manager.can_process('foo/bar/weird.json')
        assert manager.can_process('artifactstore/foo/bar/weird.json')
        assert not manager.can_process('foo/other.xml')
        assert not manager.can_process('bar/foo/baz/weird.json')
        assert not manager.can_process('service.log')
