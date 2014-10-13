from changes.config import db
from changes.models import ItemOption, Step
from changes.testutils import APITestCase


class StepDetailsTest(APITestCase):
    def test_simple(self):
        project = self.create_project()
        plan = self.create_plan(project, label='Foo')
        step = self.create_step(plan=plan)

        self.create_option(item_id=step.id, name='build.timeout', value='1')

        path = '/api/0/steps/{0}/'.format(step.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == step.id.hex
        assert data['options'] == {'build.timeout': '1'}


class UpdateStepDetailsTest(APITestCase):
    def test_requires_auth(self):
        project = self.create_project()
        plan = self.create_plan(project, label='Foo')
        step = self.create_step(plan=plan)

        path = '/api/0/steps/{0}/'.format(step.id.hex)

        resp = self.client.post(path)
        assert resp.status_code == 401

    def test_simple(self):
        self.login_default_admin()

        project = self.create_project()
        plan = self.create_plan(project, label='Foo')
        step = self.create_step(plan=plan)

        self.login_default_admin()

        path = '/api/0/steps/{0}/'.format(step.id.hex)

        resp = self.client.post(path, data={
            'order': 1,
            'implementation': 'changes.buildsteps.dummy.DummyBuildStep',
            'data': '{}',
            'build.timeout': '1',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['data'] == '{}'
        assert data['order'] == 1
        assert data['implementation'] == 'changes.buildsteps.dummy.DummyBuildStep'
        assert data['options'] == {'build.timeout': '1'}

        db.session.expire(step)

        step = Step.query.get(step.id)
        assert step.data == {}
        assert step.order == 1
        assert step.implementation == 'changes.buildsteps.dummy.DummyBuildStep'

        options = list(ItemOption.query.filter(ItemOption.item_id == step.id))
        assert len(options) == 1
        assert options[0].name == 'build.timeout'
        assert options[0].value == '1'


class DeleteStepDetailsTest(APITestCase):
    def test_requires_auth(self):
        project = self.create_project()
        plan = self.create_plan(project, label='Foo')
        step = self.create_step(plan=plan)

        path = '/api/0/steps/{0}/'.format(step.id.hex)

        resp = self.client.delete(path)
        assert resp.status_code == 401

    def test_simple(self):
        self.login_default()

        project = self.create_project()
        plan = self.create_plan(project, label='Foo')
        step = self.create_step(plan=plan)

        self.login_default_admin()

        path = '/api/0/steps/{0}/'.format(step.id.hex)

        step_id = step.id

        resp = self.client.delete(path)
        assert resp.status_code == 200

        db.session.expire_all()

        step = Step.query.get(step_id)
        assert step is None
