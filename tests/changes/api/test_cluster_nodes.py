from changes.testutils import APITestCase


class ClusterNodesTest(APITestCase):
    def test_simple(self):
        cluster_1 = self.create_cluster(label='bar')
        node_1 = self.create_node(cluster=cluster_1, label='foo')
        node_2 = self.create_node(cluster=cluster_1, label='test')

        path = '/api/0/clusters/{0}/nodes/'.format(cluster_1.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == node_1.id.hex
        assert data[1]['id'] == node_2.id.hex
