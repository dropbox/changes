from datetime import datetime
from uuid import UUID

from changes.api.serializer import serialize
from changes.models import Project, Change


def test_simple():
    change = Change(
        id=UUID(hex='33846695b2774b29a71795a009e8168a'),
        label='Hello world',
        project=Project(slug='test', name='test'),
        date_created=datetime(2013, 9, 19, 22, 15, 22),
        date_modified=datetime(2013, 9, 19, 22, 15, 23),
    )
    result = serialize(change)
    assert result['name'] == 'Hello world'
    assert result['link'] == 'http://example.com/changes/33846695b2774b29a71795a009e8168a/'
    assert result['id'] == '33846695b2774b29a71795a009e8168a'
    assert result['dateCreated'] == '2013-09-19T22:15:22'
    assert result['dateModified'] == '2013-09-19T22:15:23'
