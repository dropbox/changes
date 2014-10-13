from changes.config import db
from changes.models import ItemOption
from changes.testutils import APITestCase


class PlanOptionsListTest(APITestCase):
    def test_simple(self):
        project = self.create_project()
        plan = self.create_plan(project)

        path = '/api/0/plans/{0}/options/'.format(plan.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['build.expect-tests'] == '0'

        db.session.add(ItemOption(
            name='build.expect-tests',
            value='1',
            item_id=plan.id,
        ))
        db.session.commit()

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['build.expect-tests'] == '1'


class PlanOptionsUpdateTest(APITestCase):
    def test_simple(self):
        project = self.create_project()
        plan = self.create_plan(project)

        path = '/api/0/plans/{0}/options/'.format(plan.id.hex)

        resp = self.client.post(path, data={
            'build.expect-tests': '1',
        })
        assert resp.status_code == 401

        self.login_default()

        resp = self.client.post(path, data={
            'build.expect-tests': '1',
        })
        assert resp.status_code == 403

        self.login_default_admin()

        resp = self.client.post(path, data={
            'build.expect-tests': '1',
        })
        assert resp.status_code == 200

        options = dict(db.session.query(
            ItemOption.name, ItemOption.value
        ).filter(
            ItemOption.item_id == plan.id,
        ))

        assert options.get('build.expect-tests') == '1'
