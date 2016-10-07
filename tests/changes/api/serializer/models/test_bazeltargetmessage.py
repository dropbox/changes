from datetime import datetime

from changes.api.serializer import serialize
from changes.testutils.cases import TestCase


class BazelTargetMessageTestCase(TestCase):

    def test_correct(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        target = self.create_target(job)
        message = self.create_target_message(
            target,
            text="Test message",
            date_created=datetime(2013, 9, 19, 22, 15, 22),
        )

        result = serialize(message)
        assert result['id'] == message.id.hex
        assert result['target']['id'] == message.target_id.hex
        assert result['text'] == message.text
        assert result['dateCreated'] == '2013-09-19T22:15:22'
