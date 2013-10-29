from changes.testutils import APITestCase


class ProjectListTest(APITestCase):
    def test_simple(self):
        path = '/api/0/projects/'.format(
            self.project.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data['projects']) == 2
        assert data['projects'][0]['id'] == self.project.id.hex
        assert data['projects'][1]['id'] == self.project2.id.hex
