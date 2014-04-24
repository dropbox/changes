from changes.api.client import api_client
from changes.testutils import TestCase


class APIClientTest(TestCase):
    def test_simple(self):
        # HACK: relies on existing endpoint
        result = api_client.get('/projects/')
        assert type(result) == list
