from datetime import datetime
from uuid import uuid4

from changes.constants import Result, Status
from mock import patch, Mock
from changes.vcs.base import Vcs, RevisionResult
from changes.testutils import APITestCase


class ProjectTestHistoryTest(APITestCase):
    @patch('changes.models.Repository.get_vcs')
    def test_simple(self, get_vcs):
        all_hash_chars = "abcdefgh"
        hash_chars_with_tests = "abcfgh"

        def log_results(parent=None, branch=None, offset=0, limit=1):

            def result(id):
                return RevisionResult(
                    id=id,
                    message='hello world',
                    author='Foo <foo@example.com>',
                    author_date=datetime(2013, 9, 19, 22, 15, 21),
                )
            return iter([
                result(c * 40)
                for c in all_hash_chars
            ][offset:offset + limit])

        # Fake having a VCS and stub the returned commit log
        fake_vcs = Mock(spec=Vcs)
        fake_vcs.log.side_effect = log_results
        get_vcs.return_value = fake_vcs

        fake_id = uuid4()

        project = self.create_project()

        def create_parent_group(revision_sha):
            return self.create_test(
                job=self.create_job(
                    self.create_build(
                        project=project,
                        status=Status.finished,
                        result=Result.passed,
                        source=self.create_source(
                            project=project,
                            revision_sha=revision_sha,
                            )
                    )
                ),
                name='foo',
            )

        parent_groups = {
            c: create_parent_group(c * 40)
            for c in hash_chars_with_tests
        }

        # invalid project id
        path = '/api/0/projects/{0}/tests/{1}/history/'.format(
            fake_id.hex, parent_groups['a'].name_sha)

        resp = self.client.get(path)
        assert resp.status_code == 404

        path = '/api/0/projects/{0}/tests/{1}/history/'.format(
            project.id.hex, fake_id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 404

        path = '/api/0/projects/{0}/tests/{1}/history/'.format(
            project.id.hex, parent_groups['a'].name_sha)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)

        assert len(data) == 8
        for i, parent_group_key in enumerate(all_hash_chars):
            if parent_group_key in hash_chars_with_tests:
                assert data[i]['id'] == parent_groups[parent_group_key].id.hex
            else:
                assert data[i] is None

        # pagination
        path = '/api/0/projects/{0}/tests/{1}/history/?per_page=1'.format(
            project.id.hex, parent_groups['a'].name_sha)
        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == parent_groups['a'].id.hex

        path = '/api/0/projects/{0}/tests/{1}/history/?per_page=3&page=2'.format(
            project.id.hex, parent_groups['a'].name_sha)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)

        assert len(data) == 3
        assert data[0] is None
        assert data[1] is None
        assert data[2]['id'] == parent_groups['f'].id.hex
