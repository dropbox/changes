from datetime import datetime
from uuid import UUID

from changes.api.serializer import serialize
from changes.models import AggregateTestGroup, Job, Project


def test_simple():
    project = Project(
        id=UUID(hex='3a038b4000114157a9a8174344ff6164'),
        slug='test',
        name='test',
    )
    build = Job(id=UUID(hex='1e7958a368f44b0eb5a57372a9910d50'))

    parent = AggregateTestGroup(
        id=UUID(hex='33846695b2774b29a71745a009e8168a'),
        name='test.group',
        first_job=build,
        project=project,
        project_id=project.id,
        date_created=datetime(2013, 9, 19, 22, 15, 22),
    )
    test = AggregateTestGroup(
        id=UUID(hex='33846695b2774b29a71795a009e8168a'),
        name='test.group.ClassName',
        first_job=build,
        project=project,
        project_id=project.id,
        date_created=datetime(2013, 9, 19, 22, 15, 22),
        parent=parent,
    )
    result = serialize(test)
    assert result['name'] == 'test.group.ClassName'
    assert result['shortName'] == 'ClassName'
    assert result['id'] == '33846695b2774b29a71795a009e8168a'
    assert result['firstBuild']['id'] == '1e7958a368f44b0eb5a57372a9910d50'
    assert result['dateCreated'] == '2013-09-19T22:15:22'
