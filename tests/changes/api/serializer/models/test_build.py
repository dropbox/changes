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
        project=Project(
            slug='test', name='test', id=UUID('1e7958a368f44b0eb5a57372a9910d50'),
        ),
        project_id=UUID('1e7958a368f44b0eb5a57372a9910d50'),
        source=Source(
            revision_sha='1e7958a368f44b0eb5a57372a9910d50',
        ),
        date_created=datetime(2013, 9, 19, 22, 15, 22),
        date_started=datetime(2013, 9, 19, 22, 15, 23),
        date_finished=datetime(2013, 9, 19, 22, 15, 33),
        date_decided=datetime(2013, 9, 19, 22, 15, 43),
    )
    result = serialize(build)
    assert result['name'] == 'Hello world'
    assert result['id'] == '33846695b2774b29a71795a009e8168a'
    assert result['source']['id'] == build.source.id.hex
    assert result['target'] == 'D1234'
    assert result['message'] == 'Foo bar'
    assert result['dateCreated'] == '2013-09-19T22:15:22'
    assert result['dateStarted'] == '2013-09-19T22:15:23'
    assert result['dateFinished'] == '2013-09-19T22:15:33'
    assert result['dateDecided'] == '2013-09-19T22:15:43'
    assert result['duration'] == 10000
    assert result['link'] == 'http://example.com/projects/test/builds/{0}/'.format(build.id.hex)
