from datetime import datetime

from changes.api.serializer import serialize
from changes.testutils.cases import TestCase


class BuildMessageTestCase(TestCase):

    def test_correct(self):
        build = self.create_build(self.create_project())
        message = self.create_build_message(
            build,
            text="Test message",
            date_created=datetime(2013, 9, 19, 22, 15, 22),
        )

        result = serialize(message)
        assert result['id'] == message.id.hex
        assert result['build']['id'] == message.build_id.hex
        assert result['text'] == message.text
        assert result['dateCreated'] == '2013-09-19T22:15:22'
