from changes.config import db
from changes.models.comment import Comment
from changes.testutils import APITestCase


class BuildCommentIndexTest(APITestCase):
    def test_get(self):
        build = self.create_build(project=self.create_project())

        comment = Comment(
            build=build,
            user=self.default_user,
            text='Hello world!',
        )
        db.session.add(comment)
        db.session.commit()

        path = '/api/0/builds/{0}/comments/'.format(build.id.hex)
        resp = self.client.get(path)

        assert resp.status_code == 200, resp.data

        data = self.unserialize(resp)

        assert len(data) == 1

        assert data[0]['id'] == comment.id.hex

    def test_post(self):
        self.login_default()

        build = self.create_build(project=self.create_project())

        path = '/api/0/builds/{0}/comments/'.format(build.id.hex)
        resp = self.client.post(path, data={
            'text': 'Hello world!',
        })

        assert resp.status_code == 200, resp.data

        data = self.unserialize(resp)

        assert data['id']

        comment = Comment.query.get(data['id'])

        assert comment.user == self.default_user
        assert comment.text == 'Hello world!'
        assert comment.build == build
