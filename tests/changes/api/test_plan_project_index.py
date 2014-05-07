from changes.testutils import APITestCase


class PlanProjectIndexTest(APITestCase):
    def test_simple(self):
        project1 = self.create_project()
        project2 = self.create_project()

        plan1 = self.create_plan(label='Foo')
        plan1.projects.append(project1)
        plan1.projects.append(project2)

        path = '/api/0/plans/{0}/projects/'.format(plan1.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2


class CreatePlanProjectTest(APITestCase):
    def requires_auth(self):
        plan = self.create_plan(label='Foo')

        path = '/api/0/plans/{0}/projects/'.format(plan.id.hex)

        resp = self.client.post(path)
        assert resp.status_code == 401

    def test_simple(self):
        project1 = self.create_project()

        plan1 = self.create_plan(label='Foo')

        self.login_default_admin()

        path = '/api/0/plans/{0}/projects/'.format(plan1.id.hex)

        resp = self.client.post(path, data={
            'id': project1.id,
        })
        assert resp.status_code == 200
