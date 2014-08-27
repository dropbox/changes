from uuid import uuid4
from urllib import quote

from changes.testutils import APITestCase


class ProjectBuildListTest(APITestCase):
    def test_simple(self):
        fake_project_id = uuid4()

        project = self.create_project()
        self.create_build(project)

        project = self.create_project()
        build = self.create_build(project)

        path = '/api/0/projects/{0}/builds/'.format(fake_project_id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 404

        path = '/api/0/projects/{0}/builds/'.format(project.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build.id.hex

    def test_include_patches(self):
        project = self.create_project()
        patch = self.create_patch(repository=project.repository)
        source = self.create_source(project, patch=patch)
        build = self.create_build(project)
        self.create_build(project, source=source)

        # ensure include_patches correctly references Source.patch
        path = '/api/0/projects/{0}/builds/?include_patches=0'.format(project.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build.id.hex

        path = '/api/0/projects/{0}/builds/?include_patches=1'.format(project.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2

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

        resp = self.client.get(path + '?author=' + quote(self.default_user.email))
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
