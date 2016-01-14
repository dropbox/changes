from datetime import datetime
from uuid import UUID

from changes.api.serializer import serialize
from changes.models.log import LogSource, LogChunk


def test_simple():
    logchunk = LogChunk(
        id=UUID(hex='33846695b2774b29a71795a009e8168a'),
        source_id=UUID(hex='0b61b8a47ec844918d372d5741187b1c'),
        source=LogSource(id=UUID(hex='0b61b8a47ec844918d372d5741187b1c')),
        offset=10,
        size=7,
        text='\x1b[0;36mnotice: foo bar',
        date_created=datetime(2013, 9, 19, 22, 15, 22),
    )
    result = serialize(logchunk)
    assert result['id'] == '33846695b2774b29a71795a009e8168a'
    assert result['source']['id'] == '0b61b8a47ec844918d372d5741187b1c'
    assert result['text'] == '\x1b[0;36mnotice: foo bar'
    assert result['size'] == 7
    assert result['offset'] == 10
