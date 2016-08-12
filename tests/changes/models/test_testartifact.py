import mock

from base64 import b64encode

from changes.lib.artifact_store_mock import ArtifactStoreMock
from changes.models.testartifact import TestArtifact
from changes.testutils.cases import TestCase


class TestTestArtifact(TestCase):
    @mock.patch('changes.storage.artifactstore.ArtifactStoreClient', ArtifactStoreMock)
    def test_content_type(self):
        bucket = 'test_bucket'
        ArtifactStoreMock('').create_bucket(bucket)
        testartifact = TestArtifact(
                    name='image.png',
                    type='image',
                )
        testartifact.save_base64_content(b64encode('random'), bucket)
        assert testartifact._get_content_type() == 'image/png'

        testartifact = TestArtifact(
                    name='text.txt',
                    type='text',
                )
        testartifact.save_base64_content(b64encode('random'), bucket)
        assert testartifact._get_content_type() == 'text/plain'

        testartifact = TestArtifact(
                    name='index.html',
                    type='html',
                )
        testartifact.save_base64_content(b64encode('random'), bucket)
        assert testartifact._get_content_type() == 'text/plain'

        testartifact = TestArtifact(
                    name='index.bad_extension',
                    type='html',
                )
        testartifact.save_base64_content(b64encode('random'), bucket)
        assert testartifact._get_content_type() is None

        testartifact = TestArtifact(
                    name='no_extension',
                    type='html',
                )
        testartifact.save_base64_content(b64encode('random'), bucket)
        assert testartifact._get_content_type() is None
