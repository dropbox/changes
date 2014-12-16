from base64 import b64encode

from changes.models.testartifact import TestArtifact
from changes.testutils.cases import TestCase


class TestTestArtifact(TestCase):
    def test_content_type(self):
        testartifact = TestArtifact(
                    name='image.png',
                    type='image',
                )
        testartifact.save_base64_content(b64encode('random'))
        assert testartifact.file.get_content_type() == 'image/png'

        testartifact = TestArtifact(
                    name='text.txt',
                    type='text',
                )
        testartifact.save_base64_content(b64encode('random'))
        assert testartifact.file.get_content_type() == 'text/plain'

        testartifact = TestArtifact(
                    name='index.html',
                    type='html',
                )
        testartifact.save_base64_content(b64encode('random'))
        assert testartifact.file.get_content_type() == 'text/plain'

        testartifact = TestArtifact(
                    name='index.bad_extension',
                    type='html',
                )
        testartifact.save_base64_content(b64encode('random'))
        assert testartifact.file.get_content_type() is None

        testartifact = TestArtifact(
                    name='no_extension',
                    type='html',
                )
        testartifact.save_base64_content(b64encode('random'))
        assert testartifact.file.get_content_type() is None
