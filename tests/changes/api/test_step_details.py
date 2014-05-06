from changes.testutils import APITestCase


class StepDetailsTest(APITestCase):
    def test_simple(self):
        plan = self.create_plan(label='Foo')
        step = self.create_step(plan=plan)

        path = '/api/0/steps/{0}/'.format(step.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == step.id.hex
