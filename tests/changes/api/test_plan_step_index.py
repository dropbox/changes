from changes.models import ItemOption
from changes.testutils import APITestCase


class PlanStepIndexTest(APITestCase):
    def test_simple(self):
        project = self.create_project()
        plan = self.create_plan(project, label='Foo')

        step1 = self.create_step(plan=plan)

        self.create_option(item_id=step1.id, name='build.timeout', value='1')

        path = '/api/0/plans/{0}/steps/'.format(plan.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == step1.id.hex
        assert data[0]['options'] == {'build.timeout': '1'}


class CreatePlanStepTest(APITestCase):
    def test_requires_auth(self):
        project = self.create_project()
        plan = self.create_plan(project, label='Foo')

        path = '/api/0/plans/{0}/steps/'.format(plan.id.hex)

        resp = self.client.post(path)
        assert resp.status_code == 401

    def test_simple(self):
        project = self.create_project()
        plan = self.create_plan(project, label='Foo')

        self.login_default_admin()

        path = '/api/0/plans/{0}/steps/'.format(plan.id.hex)

        resp = self.client.post(path, data={
            'implementation': 'changes.buildsteps.dummy.DummyBuildStep',
            'build.timeout': '1',
        })
        assert resp.status_code == 201, resp.data
        data = self.unserialize(resp)
        assert data['implementation'] == 'changes.buildsteps.dummy.DummyBuildStep'
        assert data['options'] == {'build.timeout': '1'}

        assert len(plan.steps) == 1
        step = plan.steps[0]
        assert step.implementation == 'changes.buildsteps.dummy.DummyBuildStep'
        assert step.order == 0

        options = list(ItemOption.query.filter(ItemOption.item_id == step.id))
        assert len(options) == 1
        assert options[0].name == 'build.timeout'
        assert options[0].value == '1'
