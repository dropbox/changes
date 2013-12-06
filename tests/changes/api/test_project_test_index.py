from uuid import uuid4

from changes.config import db
from changes.models import AggregateTestSuite, AggregateTestGroup
from changes.testutils import APITestCase


class ProjectTestIndexTest(APITestCase):
    def test_simple(self):
        fake_project_id = uuid4()

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

        agg_group = AggregateTestGroup(
            suite=agg_suite,
            project=project,
            name='foo',
            name_sha='a' * 40,
            first_build=build,
            last_build=build,
        )
        db.session.add(agg_group)

        path = '/api/0/projects/{0}/tests/'.format(fake_project_id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 404

        path = '/api/0/projects/{0}/tests/'.format(project.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data['tests']) == 1
        assert data['tests'][0]['id'] == agg_group.id.hex
