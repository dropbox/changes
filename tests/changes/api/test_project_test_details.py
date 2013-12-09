from uuid import uuid4

from changes.config import db
from changes.models import AggregateTestGroup, TestGroup
from changes.testutils import APITestCase


class ProjectTestDetailsTest(APITestCase):
    def test_simple(self):
        fake_id = uuid4()

        self.create_build(self.project)

        project = self.create_project()
        build = self.create_build(project)

        parent_agg_group = AggregateTestGroup(
            project=project,
            name='foo',
            name_sha='a' * 40,
            first_build=build,
            last_build=build,
        )
        db.session.add(parent_agg_group)

        parent_group = TestGroup(
            build=build,
            project=project,
            name=parent_agg_group.name,
            name_sha=parent_agg_group.name_sha,
        )
        db.session.add(parent_group)

        child_agg_group = AggregateTestGroup(
            project=project,
            name='foo.bar',
            name_sha='b' * 40,
            first_build=build,
            last_build=build,
            parent=parent_agg_group,
        )
        db.session.add(child_agg_group)

        child_group = TestGroup(
            build=build,
            project=project,
            parent=parent_group,
            name=child_agg_group.name,
            name_sha=child_agg_group.name_sha,
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
            project.id.hex, parent_agg_group.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['test']['id'] == parent_agg_group.id.hex
        assert data['test']['lastTest']['id'] == parent_group.id.hex
        assert len(data['childTests']) == 1
        assert data['childTests'][0]['id'] == child_agg_group.id.hex
        assert data['childTests'][0]['lastTest']['id'] == child_group.id.hex
        assert len(data['context']) == 1
        assert data['context'][0]['id'] == parent_agg_group.id.hex
