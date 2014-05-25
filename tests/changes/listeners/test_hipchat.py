from __future__ import absolute_import

import mock
import responses

from urllib.parse import parse_qsl

from changes.constants import Result
from changes.listeners.hipchat import build_finished_handler
from changes.testutils import TestCase


class HipChatTest(TestCase):
    @responses.activate
    @mock.patch('changes.listeners.hipchat.get_options')
    def test_simple(self, get_options):
        build = self.create_build(self.project, result=Result.failed)

        responses.add(
            responses.POST, 'https://api.hipchat.com/v1/rooms/message',
            body='{"status": "sent"}')

        get_options.return_value = {
            'hipchat.notify': '1',
            'hipchat.room': 'Awesome',
        }

        build_finished_handler(build_id=build.id.hex)

        get_options.assert_called_once_with(build.project_id)

        assert len(responses.calls) == 1
        assert responses.calls[0].request.url == 'https://api.hipchat.com/v1/rooms/message'

        assert sorted(parse_qsl(responses.calls[0].request.body)) == [
            ('auth_token', 'abc'),
            ('color', 'red'),
            ('from', 'Changes'),
            ('message', 'Build Failed - <a href="http://example.com/projects/test/builds/{build_id}/">test #1</a> ({target})'.format(
                build_id=build.id.hex,
                target=build.source.revision_sha,
            )),
            ('notify', '1'),
            ('room_id', 'Awesome'),
        ]
