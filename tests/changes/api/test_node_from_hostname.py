from changes.testutils import APITestCase


class NodeFromHostnameTest(APITestCase):
    def test_simple(self):
        node = self.create_node(label='ip-127-0-0-1')
        path = '/api/0/nodes/hostname/{0}/'.format(node.label)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == node.id.hex

    def test_not_found(self):
        self.create_node(label='ip-127-0-0-1')
        path = '/api/0/nodes/hostname/{0}/'.format('ip-0-0-0-0')

        resp = self.client.get(path)
        assert resp.status_code == 404
