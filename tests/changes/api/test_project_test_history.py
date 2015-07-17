from datetime import datetime
from uuid import uuid4

from changes.constants import Result, Status
from mock import patch, Mock
from changes.vcs.base import Vcs, RevisionResult
from changes.testutils import APITestCase


class ProjectTestHistoryTest(APITestCase):
    @patch('changes.models.Repository.get_vcs')
    def test_simple(self, get_vcs):

        def log_results(parent=None, branch=None, offset=0, limit=1):
            # assert not branch
            return iter([
                RevisionResult(
                    id='a' * 40,
                    message='hello world',
                    author='Foo <foo@example.com>',
                    author_date=datetime(2013, 9, 19, 22, 15, 21),
                    ),
                RevisionResult(
                    id='b' * 40,
                    message='hello world',
                    author='Foo <foo@example.com>',
                    author_date=datetime(2013, 9, 19, 22, 15, 21),

                )
            ][offset:offset + limit])

        # Fake having a VCS and stub the returned commit log
        fake_vcs = Mock(spec=Vcs)
        fake_vcs.log.side_effect = log_results
        get_vcs.return_value = fake_vcs

        fake_id = uuid4()

        project = self.create_project()

        previous_source = self.create_source(
            project=project,
            revision_sha='b' * 40,
        )
        previous_build = self.create_build(
            project=project,
            status=Status.finished,
            result=Result.passed,
            source=previous_source
        )
        previous_job = self.create_job(previous_build)

        source = self.create_source(
            project=project,
            revision_sha='a' * 40,
        )
        build = self.create_build(
            project=project,
            status=Status.finished,
            result=Result.passed,
            source=source
        )
        job = self.create_job(build)

        previous_parent_group = self.create_test(
            job=previous_job,
            name='foo',
        )

        parent_group = self.create_test(
            job=job,
            name='foo',
        )

        # invalid project id
        path = '/api/0/projects/{0}/tests/{1}/history/'.format(
            fake_id.hex, parent_group.name_sha)

        resp = self.client.get(path)
        assert resp.status_code == 404

        path = '/api/0/projects/{0}/tests/{1}/history/'.format(
            project.id.hex, fake_id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 404

        path = '/api/0/projects/{0}/tests/{1}/history/'.format(
            project.id.hex, parent_group.name_sha)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)

        assert len(data) == 2
        assert data[1]['id'] == previous_parent_group.id.hex
        assert data[0]['id'] == parent_group.id.hex

        # pagination
        path = '/api/0/projects/{0}/tests/{1}/history/?per_page=1'.format(
            project.id.hex, parent_group.name_sha)
        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == parent_group.id.hex

        path = '/api/0/projects/{0}/tests/{1}/history/?per_page=1&{2}'.format(
            project.id.hex, parent_group.name_sha, 'page=2')

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == previous_parent_group.id.hex
