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
            MAX_ARTIFACT_SIZE = 200

        class _OtherHandler(ArtifactHandler):
            FILENAMES = ('/other.xml',)
            MAX_ARTIFACT_SIZE = 200

        manager = Manager([_CovHandler, _OtherHandler])
        jobstep = self.create_any_jobstep()

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

    @mock.patch.object(ArtifactHandler, 'process')
    @mock.patch.object(ArtifactHandler, 'report_malformed')
    def test_process_too_large(self, report_malformed, process):
        file_sizes = {
            'large/size.xml': 1000,
            'medium/size.xml': 500,
            'small/size.xml': 10,
        }

        class _Handler(ArtifactHandler):
            FILENAMES = ('size.xml',)
            MAX_ARTIFACT_BYTES = 500

        manager = Manager([_Handler])
        jobstep = self.create_any_jobstep()

        for name, size in file_sizes.iteritems():
            process.reset_mock()
            report_malformed.reset_mock()
            artifact = self.create_artifact(
                step=jobstep,
                name=name,
            )
            artifact.file.save(StringIO('a' * size), artifact.name)
            if size > _Handler.MAX_ARTIFACT_BYTES:
                manager.process(artifact)
                assert not process.called, \
                    "Artifact %s should not have been processed" % (artifact.name,)
                assert report_malformed.called, \
                    "Artifact %s should have been reported as malformed" % (artifact.name,)
            else:
                manager.process(artifact)
                assert process.called, \
                    "Artifact %s should have been processed" % (artifact.name,)
                assert not report_malformed.called, \
                    "Artifact %s should not have been reported as malformed" % (artifact.name,)

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
