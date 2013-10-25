from changes.api.serializer import serialize
from changes.constants import Cause


def test_simple():
    result = serialize(Cause.retry)
    assert result['id'] == 'retry'
    assert result['name'] == 'Retry'
