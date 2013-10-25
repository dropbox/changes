from datetime import datetime
from uuid import UUID

from changes.api.serializer import serialize
from changes.models import Project


def test_simple():
    project = Project(
        id=UUID(hex='33846695b2774b29a71795a009e8168a'),
        slug='hello-world',
        name='Hello world',
        date_created=datetime(2013, 9, 19, 22, 15, 22),
    )
    result = serialize(project)
    assert result['name'] == 'Hello world'
    assert result['id'] == '33846695b2774b29a71795a009e8168a'
    assert result['slug'] == 'hello-world'
    assert result['dateCreated'] == '2013-09-19T22:15:22'
