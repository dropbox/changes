from uuid import uuid4

from changes.config import db
from changes.models import Author
from changes.testutils import APITestCase


class AuthorBuildListTest(APITestCase):
    def test_simple(self):
        fake_author_id = uuid4()

        build = self.create_build(self.project)
        self.create_job(build)

        path = '/api/0/authors/{0}/builds/'.format(fake_author_id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data['builds']) == 0

        author = Author(email='foo@example.com', name='Foo Bar')
        db.session.add(author)
        build = self.create_build(self.project, author=author)
        job = self.create_job(build)

        path = '/api/0/authors/{0}/builds/'.format(author.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == job.id.hex
