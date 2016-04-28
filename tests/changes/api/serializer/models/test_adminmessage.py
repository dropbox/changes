from datetime import datetime
from uuid import UUID

from changes.api.serializer import serialize
from changes.models.adminmessage import AdminMessage
from changes.testutils import TestCase


class AdminMessageTest(TestCase):
    def test_simple(self):
        message = AdminMessage(
            id=UUID(hex='33846695b2774b29a71795a009e8168a'),
            message='Foo bar',
            user=self.create_user(
                    email='foo@example.com',
            ),
            date_created=datetime(2013, 9, 19, 22, 15, 22),
        )
        result = serialize(message)
        assert result['id'] == '33846695b2774b29a71795a009e8168a'
        assert result['user']['id'] == message.user.id.hex
        assert result['message'] == 'Foo bar'
        assert result['dateCreated'] == '2013-09-19T22:15:22'
