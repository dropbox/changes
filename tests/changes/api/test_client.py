from changes.api.client import api_client
from changes.testutils import TestCase


class APIClientTest(TestCase):
    def test_simple(self):
        # HACK: relies on existing endpoint
        result = api_client.get('/api/0/projects/')
        assert result.status_code == 200
        assert result.data
