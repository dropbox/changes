from changes.testutils import APITestCase


class NodeDetailsTest(APITestCase):
    def test_simple(self):
        node = self.create_node()
        path = '/api/0/nodes/{0}/'.format(node.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == node.id.hex
