from changes.config import db
from changes.models import Step
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


class UpdateStepDetailsTest(APITestCase):
    def requires_auth(self):
        plan = self.create_plan(label='Foo')
        step = self.create_step(plan=plan)

        path = '/api/0/steps/{0}/'.format(step.id.hex)

        resp = self.client.post(path)
        assert resp.status_code == 401

    def test_simple(self):
        self.login_default_admin()

        plan = self.create_plan(label='Foo')
        step = self.create_step(plan=plan)

        self.login_default_admin()

        path = '/api/0/steps/{0}/'.format(step.id.hex)

        resp = self.client.post(path, data={
            'order': 1,
            'implementation': 'changes.buildsteps.dummy.DummyBuildStep',
            'data': '{}',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['data'] == '{}'
        assert data['order'] == 1
        assert data['implementation'] == 'changes.buildsteps.dummy.DummyBuildStep'

        db.session.expire(step)

        step = Step.query.get(step.id)
        assert step.data == {}
        assert step.order == 1
        assert step.implementation == 'changes.buildsteps.dummy.DummyBuildStep'


class DeleteStepDetailsTest(APITestCase):
    def requires_auth(self):
        plan = self.create_plan(label='Foo')
        step = self.create_step(plan=plan)

        path = '/api/0/steps/{0}/'.format(step.id.hex)

        resp = self.client.delete(path)
        assert resp.status_code == 401

    def test_simple(self):
        self.login_default()

        plan = self.create_plan(label='Foo')
        step = self.create_step(plan=plan)

        self.login_default_admin()

        path = '/api/0/steps/{0}/'.format(step.id.hex)

        step_id = step.id

        resp = self.client.delete(path)
        assert resp.status_code == 200

        db.session.expire_all()

        step = Step.query.get(step_id)
        assert step is None
