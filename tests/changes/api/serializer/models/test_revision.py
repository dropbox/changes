from datetime import datetime

from changes.api.serializer import serialize
from changes.models import Revision, Repository, Author


def test_simple():
    revision = Revision(
        sha='33846695b2774b29a71795a009e8168a',
        repository=Repository(),
        author=Author(
            name='Foo Bar',
            email='foo@example.com',
        ),
        message='hello world',
        date_created=datetime(2013, 9, 19, 22, 15, 22),
    )
    result = serialize(revision)
    assert result['id'] == '33846695b2774b29a71795a009e8168a'
    assert result['author']['name'] == 'Foo Bar'
    assert result['author']['email'] == 'foo@example.com'
    assert result['message'] == 'hello world'
    assert result['dateCreated'] == '2013-09-19T22:15:22'
