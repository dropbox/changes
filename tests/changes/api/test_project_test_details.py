from uuid import uuid4

from changes.config import db
from changes.models import AggregateTestSuite, AggregateTestGroup
from changes.testutils import APITestCase


class ProjectTestDetailsTest(APITestCase):
    def test_simple(self):
        fake_id = uuid4()

        self.create_build(self.project)

        project = self.create_project()
        build = self.create_build(project)

        agg_suite = AggregateTestSuite(
            project=project,
            name='default',
            name_sha='a' * 40,
            first_build=build,
            last_build=build,
        )
        db.session.add(agg_suite)

        parent_group = AggregateTestGroup(
            suite=agg_suite,
            project=project,
            name='foo',
            name_sha='a' * 40,
            first_build=build,
            last_build=build,
        )
        db.session.add(parent_group)

        child_group = AggregateTestGroup(
            suite=agg_suite,
            project=project,
            name='foo.bar',
            name_sha='b' * 40,
            first_build=build,
            last_build=build,
            parent=parent_group,
        )
        db.session.add(child_group)

        path = '/api/0/projects/{0}/tests/'.format(fake_id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 404

        path = '/api/0/projects/{0}/tests/{1}/'.format(
            project.id.hex, fake_id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 404

        path = '/api/0/projects/{0}/tests/{1}/'.format(
            project.id.hex, parent_group.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['test']['id'] == parent_group.id.hex
        assert len(data['childTests']) == 1
        assert data['childTests'][0]['id'] == child_group.id.hex
