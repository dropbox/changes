from datetime import datetime
from uuid import UUID

from changes.api.serializer import serialize
from changes.constants import Result
from changes.models import TestCase, Job, Project


def test_simple():
    testcase = TestCase(
        id=UUID(hex='33846695b2774b29a71795a009e8168a'),
        package='test.group.ClassName',
        name='test_foo',
        job=Job(id=UUID(hex='1e7958a368f44b0eb5a57372a9910d50')),
        project=Project(slug='test', name='test'),
        duration=134,
        result=Result.failed,
        date_created=datetime(2013, 9, 19, 22, 15, 22),
    )
    result = serialize(testcase)
    assert result['id'] == '33846695b2774b29a71795a009e8168a'
    assert result['name'] == 'test_foo'
    assert result['package'] == 'test.group.ClassName'
    assert result['dateCreated'] == '2013-09-19T22:15:22'
    assert result['result']['id'] == 'failed'
    assert result['duration'] == 134


def test_implicit_package():
    testcase = TestCase(
        id=UUID(hex='33846695b2774b29a71795a009e8168a'),
        name='test.group.ClassName.test_foo',
        job=Job(id=UUID(hex='1e7958a368f44b0eb5a57372a9910d50')),
        project=Project(slug='test', name='test'),
        duration=134,
        result=Result.failed,
        date_created=datetime(2013, 9, 19, 22, 15, 22),
    )
    result = serialize(testcase)
    assert result['id'] == '33846695b2774b29a71795a009e8168a'
    assert result['name'] == 'test_foo'
    assert result['package'] == 'test.group.ClassName'
    assert result['dateCreated'] == '2013-09-19T22:15:22'
    assert result['result']['id'] == 'failed'
    assert result['duration'] == 134


def test_implicit_package_only_name():
    testcase = TestCase(
        id=UUID(hex='33846695b2774b29a71795a009e8168a'),
        name='test_foo',
        job=Job(id=UUID(hex='1e7958a368f44b0eb5a57372a9910d50')),
        project=Project(slug='test', name='test'),
        duration=134,
        result=Result.failed,
        date_created=datetime(2013, 9, 19, 22, 15, 22),
    )
    result = serialize(testcase)
    assert result['id'] == '33846695b2774b29a71795a009e8168a'
    assert result['name'] == 'test_foo'
    assert result['package'] is None
    assert result['dateCreated'] == '2013-09-19T22:15:22'
    assert result['result']['id'] == 'failed'
    assert result['duration'] == 134
