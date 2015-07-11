from changes.models import Plan
from changes.testutils import APITestCase


class PlanDetailsTest(APITestCase):
    def test_simple(self):
        project1 = self.create_project()

        plan1 = self.create_plan(project1, label='Foo')

        path = '/api/0/plans/{0}/'.format(plan1.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == plan1.id.hex


class UpdatePlanTest(APITestCase):
    def test_simple(self):
        project = self.create_project()
        plan = self.create_plan(project, label='Foo')

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

    def test_set_snapshot_plan_id(self):
        project = self.create_project()
        plan = self.create_plan(project, label='Foo')
        other_plan = self.create_plan(project, label='Bar')

        path = '/api/0/plans/{0}/'.format(plan.id.hex)

        self.login_default_admin()
        resp = self.client.post(path, data={
            'snapshot_plan_id': other_plan.id.hex,
        })
        assert resp.status_code == 200

        plan = Plan.query.get(plan.id)
        assert plan.snapshot_plan_id == other_plan.id
