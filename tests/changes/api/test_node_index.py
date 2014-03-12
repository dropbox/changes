from changes.testutils import APITestCase


class NodeDetailsTest(APITestCase):
    def test_simple(self):
        node_1 = self.create_node(label='bar')
        node_2 = self.create_node(label='foo')
        path = '/api/0/nodes/'

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == node_1.id.hex
        assert data[1]['id'] == node_2.id.hex
