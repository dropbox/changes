from datetime import datetime
from uuid import UUID

from changes.api.serializer import serialize
from changes.models import LogSource, Job, JobStep


def test_simple():
    logsource = LogSource(
        id=UUID(hex='33846695b2774b29a71795a009e8168a'),
        job_id=UUID(hex='2e18a7cbc0c24316b2ef9d41fea191d6'),
        job=Job(id=UUID(hex='2e18a7cbc0c24316b2ef9d41fea191d6')),
        step=JobStep(
            id=UUID(hex='36c7af5e56aa4a7fbf076e13ac00a866'),
            phase_id=UUID(hex='46c7af5e56aa4a7fbf076e13ac00a866')
        ),
        name='console',
        date_created=datetime(2013, 9, 19, 22, 15, 22),
    )
    result = serialize(logsource)
    assert result['id'] == '33846695b2774b29a71795a009e8168a'
    assert result['name'] == 'console'
    assert result['dateCreated'] == '2013-09-19T22:15:22'
    assert result['step']['id'] == '36c7af5e56aa4a7fbf076e13ac00a866'
