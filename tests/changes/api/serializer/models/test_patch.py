from datetime import datetime
from uuid import UUID

from changes.api.serializer import serialize
from changes.models import Patch
from changes.testutils import SAMPLE_DIFF, TestCase


class PatchTest(TestCase):
    def test_simple(self):
        patch = Patch(
            id=UUID(hex='33846695b2774b29a71795a009e8168a'),
            diff=SAMPLE_DIFF,
            parent_revision_sha='1e7958a368f44b0eb5a57372a9910d50',
            date_created=datetime(2013, 9, 19, 22, 15, 22),
        )
        result = serialize(patch)
        assert result['link'] == 'http://example.com/patches/33846695b2774b29a71795a009e8168a/'
        assert result['id'] == '33846695b2774b29a71795a009e8168a'
        assert result['parentRevision'] == {
            'sha': '1e7958a368f44b0eb5a57372a9910d50',
        }
        assert result['dateCreated'] == '2013-09-19T22:15:22'
        assert result['diff'] == SAMPLE_DIFF
