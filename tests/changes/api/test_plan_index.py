from changes.testutils import APITestCase


class PlanIndexTest(APITestCase):
    path = '/api/0/plans/'

    def test_simple(self):
        plan1 = self.plan
        plan2 = self.create_plan(label='Bar')

        resp = self.client.get(self.path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        assert data[0]['id'] == plan2.id.hex
        assert data[1]['id'] == plan1.id.hex


class CreatePlanTest(APITestCase):
    path = '/api/0/plans/'

    def requires_auth(self):
        resp = self.client.post(self.path, data={
            'name': 'Bar',
        })
        assert resp.status_code == 401

    def test_simple(self):
        self.login_default_admin()

        resp = self.client.post(self.path, data={
            'name': 'Bar',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['name'] == 'Bar'
