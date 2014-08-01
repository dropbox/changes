from uuid import uuid4

from changes.config import db
from changes.models import Author
from changes.testutils import APITestCase


class AuthorBuildListTest(APITestCase):
    def test_simple(self):
        fake_author_id = uuid4()

        project = self.create_project()

        self.create_build(project)

        path = '/api/0/authors/{0}/builds/'.format(fake_author_id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 404
        data = self.unserialize(resp)
        assert len(data) == 0

        author = Author(email=self.default_user.email, name='Foo Bar')
        db.session.add(author)
        build = self.create_build(project, author=author)

        path = '/api/0/authors/{0}/builds/'.format(author.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build.id.hex

        path = '/api/0/authors/me/builds/'

        resp = self.client.get(path)
        assert resp.status_code == 401

        self.login(self.default_user)

        path = '/api/0/authors/me/builds/'

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build.id.hex

        username, domain = self.default_user.email.split('@', 1)
        author = self.create_author('{}+foo@{}'.format(username, domain))
        self.create_build(project, author=author)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 2
