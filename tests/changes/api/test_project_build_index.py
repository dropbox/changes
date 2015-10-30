from uuid import uuid4
from urllib import quote

from changes.constants import Cause, Result
from changes.testutils import APITestCase

# flake8: noqa


class ProjectBuildListTest(APITestCase):

    def test_simple(self):

        fake_project_id = uuid4()

        project = self.create_project()
        self.create_build(project)

        project1 = self.create_project()
        build1 = self.create_build(project1, label='test', target='D1234',
                                   result=Result.passed)
        project2 = self.create_project()
        build2 = self.create_build(project2, label='test', target='D1234', tags=['foo'],
                                   result=Result.failed)

        path = '/api/0/projects/{0}/builds/'.format(fake_project_id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 404

        path = '/api/0/projects/{0}/builds/'.format(project1.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build1.id.hex

        resp = self.client.get(path + '?source=D1234')
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build1.id.hex

        resp = self.client.get(path + '?query=D1234')
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build1.id.hex

        resp = self.client.get(path + '?query=test')
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build1.id.hex

        resp = self.client.get(path + '?query=something_impossible')
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 0

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build1.id.hex

        path = '/api/0/projects/{0}/builds/'.format(project2.id.hex)

        resp = self.client.get(path + '?result=failed')
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build2.id.hex

        resp = self.client.get(path + '?result=aborted')
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 0

        build3 = self.create_build(project2, label='test', target='D12345', tags=['bar'],
                                   result=Result.failed)

        resp = self.client.get(path + '?tag=foo')
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build2.id.hex

        resp = self.client.get(path + '?tag=bar')
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build3.id.hex

    def test_more_searches(self):
        project1 = self.create_project()

        # all hashes are 8 characters, followed by abcd
        build1 = self.create_build(project1, label='First commit!',
                                   target='deadbeefabcd')
        build2 = self.create_build(project1, label='Second commit!',
                                   target='dabbad00abcd')
        build3 = self.create_build(project1, label='rThird commit!',
                                   target='facefeedabcd')

        path = '/api/0/projects/{0}/builds/'.format(project1.id.hex)

        queries_to_results = [
            # search by label
            ("First",           [build1]),
            ("rThird",          [build3]),
            ("Fifth",           []),
            ("commit",          [build1, build2, build3]),

            # search by hex, the first few hex characters, and a longer hex
            # phrase
            ("deadbeefabcd",    [build1]),
            ("dabba",           [build2]),
            ("facefeedabcdef",  [build3]),

            # only prefix matches
            ("abcd",            []),

            # phabricator test
            ("rREPOdeadbeefabcd",    [build1]),
            ("rMEPOdabbad00",        [build2]),
            ("rZEPOfacefeedabcdef",  [build3]),
        ]

        errmsg = "test_more_searches failed with search term %s"

        for term, expected_builds in queries_to_results:
            resp = self.client.get(path + '?query=' + term)
            assert resp.status_code == 200, errmsg % term
            data = self.unserialize(resp)
            assert len(data) == len(expected_builds), errmsg.format(term)
            assert set([d['id'] for d in data]) == \
                set([b.id.hex for b in expected_builds]), errmsg % term

    def test_include_patches(self):
        project = self.create_project()
        patch = self.create_patch(repository=project.repository)
        source = self.create_source(project, patch=patch)
        build = self.create_build(project)
        self.create_build(project, source=source)

        # ensure include_patches correctly references Source.patch
        path = '/api/0/projects/{0}/builds/?include_patches=0'.format(
            project.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build.id.hex

        path = '/api/0/projects/{0}/builds/?include_patches=1'.format(
            project.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2

    def test_patches_only(self):
        project = self.create_project()
        patch = self.create_patch(repository=project.repository)
        source = self.create_source(project, patch=patch)
        self.create_build(project)
        patch_build = self.create_build(project, source=source)

        path = '/api/0/projects/{0}/builds/?patches_only=1'.format(
            project.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == patch_build.id.hex

    def test_by_cause(self):
        project = self.create_project()
        patch = self.create_patch(repository=project.repository)
        source = self.create_source(project, patch=patch)
        self.create_build(project)
        push_build = self.create_build(project, source=source, cause=Cause.push)
        push_build2 = self.create_build(project, source=source, cause=Cause.push)
        snapshot_build = self.create_build(project, source=source, cause=Cause.snapshot)

        snapshot_path = '/api/0/projects/{0}/builds/?cause=snapshot'.format(
            project.id.hex)
        push_path = '/api/0/projects/{0}/builds/?cause=push'.format(
            project.id.hex)

        resp = self.client.get(snapshot_path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == snapshot_build.id.hex

        resp = self.client.get(push_path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
        push_build_ids = [push_build.id.hex, push_build2.id.hex]
        assert data[0]['id'] in push_build_ids
        assert data[1]['id'] in push_build_ids

    def test_author(self):
        project = self.create_project()
        patch = self.create_patch(repository=project.repository)
        source = self.create_source(project, patch=patch)
        author = self.create_author(email=self.default_user.email)
        build = self.create_build(project, author=author)
        self.create_build(project, source=source)

        # ensure include_patches correctly references Source.patch
        path = '/api/0/projects/{0}/builds/'.format(project.id.hex)

        resp = self.client.get(path + '?author=bizbaz@example.com')
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        assert len(data) == 0

        resp = self.client.get(
            path + '?author=' + quote(self.default_user.email))
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build.id.hex

        resp = self.client.get(path + '?author=me')
        assert resp.status_code == 400, resp.data

        self.login_default()

        resp = self.client.get(path + '?author=me')
        assert resp.status_code == 200, resp.data
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build.id.hex
