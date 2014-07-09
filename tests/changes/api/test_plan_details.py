from changes.models import Plan
from changes.testutils import APITestCase


class PlanDetailsTest(APITestCase):
    def test_simple(self):
        project1 = self.create_project()
        project2 = self.create_project()

        plan1 = self.create_plan(label='Foo')
        plan1.projects.append(project1)
        plan1.projects.append(project2)

        path = '/api/0/plans/{0}/'.format(plan1.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == plan1.id.hex
        assert len(data['projects']) == 2
        assert data['projects'][0]['id'] == project1.id.hex
        assert data['projects'][1]['id'] == project2.id.hex


class UpdatePlanTest(APITestCase):
    def test_simple(self):
        plan = self.create_plan(label='Foo')

        path = '/api/0/plans/{0}/'.format(plan.id.hex)

        # ensure endpoint requires authentication
        resp = self.client.post(path, data={
            'name': 'Bar'
        })
        assert resp.status_code == 401

        self.login_default()

        # ensure endpoint requires admin
        resp = self.client.post(path, data={
            'name': 'Bar'
        })
        assert resp.status_code == 403

        self.login_default_admin()

        # test valid params
        resp = self.client.post(path, data={
            'name': 'Bar'
        })
        assert resp.status_code == 200

        data = self.unserialize(resp)
        assert data['name'] == 'Bar'

        plan = Plan.query.get(plan.id)
        assert plan.label == 'Bar'
