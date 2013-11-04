from datetime import datetime
from uuid import UUID

from changes.api.serializer import serialize
from changes.models import TestGroup, Build, Project


def test_simple():
    testgroup = TestGroup(
        id=UUID(hex='33846695b2774b29a71795a009e8168a'),
        name='test.group.ClassName',
        build=Build(id=UUID(hex='1e7958a368f44b0eb5a57372a9910d50')),
        project=Project(slug='test', name='test'),
        duration=134,
        num_tests=5,
        num_failed=2,
        date_created=datetime(2013, 9, 19, 22, 15, 22),
    )
    result = serialize(testgroup)
    assert result['name'] == 'test.group.ClassName'
    assert result['id'] == '33846695b2774b29a71795a009e8168a'
    assert result['numTests'] == 5
    assert result['numFailures'] == 2
    assert result['dateCreated'] == '2013-09-19T22:15:22'
    assert result['duration'] == 134
