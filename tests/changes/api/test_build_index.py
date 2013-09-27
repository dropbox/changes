from changes.testutils import APITestCase


class BuildListTest(APITestCase):
    def test_simple(self):
        build = self.create_build(self.project)
        build2 = self.create_build(self.project2)

        resp = self.client.get('/api/0/builds/')
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data['builds']) == 2
        assert data['builds'][0]['id'] == build2.id.hex
        assert data['builds'][1]['id'] == build.id.hex


class BuildCreateTest(APITestCase):
    def test_simple(self):
        resp = self.client.post('/api/0/builds/', data={
            'project': self.project.slug,
            'sha': 'a' * 40,
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['build']['id']
