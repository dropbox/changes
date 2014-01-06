from datetime import datetime
from uuid import UUID

from changes.api.serializer import serialize
from changes.models import Build, Project, Source


def test_simple():
    build = Build(
        id=UUID(hex='33846695b2774b29a71795a009e8168a'),
        label='Hello world',
        target='D1234',
        message='Foo bar',
        project=Project(slug='test', name='test'),
        source=Source(
            revision_sha='1e7958a368f44b0eb5a57372a9910d50',
        ),
        date_created=datetime(2013, 9, 19, 22, 15, 22),
        date_started=datetime(2013, 9, 19, 22, 15, 23),
        date_finished=datetime(2013, 9, 19, 22, 15, 33),
    )
    result = serialize(build)
    assert result['name'] == 'Hello world'
    assert result['link'] == '/builds/33846695b2774b29a71795a009e8168a/'
    assert result['id'] == '33846695b2774b29a71795a009e8168a'
    assert result['source']['id'] == build.source.id.hex
    assert result['target'] == 'D1234'
    assert result['message'] == 'Foo bar'
    assert result['dateCreated'] == '2013-09-19T22:15:22'
    assert result['dateStarted'] == '2013-09-19T22:15:23'
    assert result['dateFinished'] == '2013-09-19T22:15:33'
    assert result['duration'] == 10000
