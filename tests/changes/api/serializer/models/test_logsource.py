from datetime import datetime
from uuid import UUID

from changes.api.serializer import serialize
from changes.models import LogSource, Job


def test_simple():
    logsource = LogSource(
        id=UUID(hex='33846695b2774b29a71795a009e8168a'),
        job_id=UUID(hex='2e18a7cbc0c24316b2ef9d41fea191d6'),
        job=Job(id=UUID(hex='2e18a7cbc0c24316b2ef9d41fea191d6')),
        name='console',
        date_created=datetime(2013, 9, 19, 22, 15, 22),
    )
    result = serialize(logsource)
    assert result['id'] == '33846695b2774b29a71795a009e8168a'
    assert result['name'] == 'console'
    assert result['link'] == 'http://example.com/jobs/2e18a7cbc0c24316b2ef9d41fea191d6/logs/33846695b2774b29a71795a009e8168a/'
    assert result['dateCreated'] == '2013-09-19T22:15:22'
