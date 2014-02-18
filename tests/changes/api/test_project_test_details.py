from uuid import uuid4

from changes.constants import Result, Status
from changes.config import db
from changes.models import AggregateTestGroup, TestGroup
from changes.testutils import APITestCase


class ProjectTestDetailsTest(APITestCase):
    def test_simple(self):
        fake_id = uuid4()

        project = self.create_project()

        previous_build = self.create_build(
            project=project,
            status=Status.finished,
            result=Result.passed,
        )
        previous_job = self.create_job(previous_build)

        build = self.create_build(
            project=project,
            status=Status.finished,
            result=Result.passed,
        )
        job = self.create_job(build)

        parent_agg_group = AggregateTestGroup(
            project=project,
            name='foo',
            name_sha='a' * 40,
            first_job=previous_job,
            last_job=job,
        )
        db.session.add(parent_agg_group)

        previous_parent_group = TestGroup(
            job=previous_job,
            project=project,
            name=parent_agg_group.name,
            name_sha=parent_agg_group.name_sha,
        )
        db.session.add(previous_parent_group)

        parent_group = TestGroup(
            job=job,
            project=project,
            name=parent_agg_group.name,
            name_sha=parent_agg_group.name_sha,
        )
        db.session.add(parent_group)

        child_agg_group = AggregateTestGroup(
            project=project,
            name='foo.bar',
            name_sha='b' * 40,
            first_job=job,
            last_job=job,
            parent=parent_agg_group,
        )
        db.session.add(child_agg_group)

        child_group = TestGroup(
            job=job,
            project=project,
            parent=parent_group,
            name=child_agg_group.name,
            name_sha=child_agg_group.name_sha,
        )
        db.session.add(child_group)

        # invalid project id
        path = '/api/0/projects/{0}/tests/{1}/'.format(
            fake_id.hex, parent_agg_group.id.hex)

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
        assert len(data['previousRuns']) == 2
        assert data['previousRuns'][1]['id'] == previous_parent_group.id.hex
        assert data['previousRuns'][0]['id'] == parent_group.id.hex
