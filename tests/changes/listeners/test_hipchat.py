from __future__ import absolute_import

import mock
import responses

from changes.constants import Result
from changes.listeners.hipchat import build_finished_handler
from changes.testutils import TestCase


class HipChatTest(TestCase):
    @responses.activate
    @mock.patch('changes.listeners.hipchat.get_options')
    def test_simple(self, get_options):
        project = self.create_project(name='test', slug='test')
        build = self.create_build(project, result=Result.failed)

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
        assert responses.calls[0].request.body == \
            'from=Changes&color=red' \
            '&auth_token=abc' \
            '&room_id=Awesome' \
            '&notify=1' \
            '&message=Build+Failed+-+%3Ca+href%3D%22http%3A%2F%2Fexample.com%2Fprojects%2Ftest%2Fbuilds%2F{build_id}%2F%22%3Etest+%231%3C%2Fa%3E+%28{target}%29'.format(
                build_id=build.id.hex,
                target=build.source.revision_sha,
            )
