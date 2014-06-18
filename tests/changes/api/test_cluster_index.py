from changes.testutils import APITestCase


class ClusterIndexTest(APITestCase):
    def test_simple(self):
        cluster_1 = self.create_cluster(label='bar')
        cluster_2 = self.create_cluster(label='foo')
        path = '/api/0/clusters/'

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == cluster_1.id.hex
        assert data[1]['id'] == cluster_2.id.hex
