from changes.testutils import APITestCase


class ClusterIndexTest(APITestCase):
    def test_simple(self):
        cluster_1 = self.create_cluster(label='bar')
        path = '/api/0/clusters/{0}/'.format(cluster_1.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == cluster_1.id.hex
