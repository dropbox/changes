from datetime import datetime

from changes.api.serializer import serialize
from changes.testutils import TestCase


class RevisionTest(TestCase):
    def test_simple(self):
        revision = self.create_revision(
            sha='33846695b2774b29a71795a009e8168a',
            repository=self.create_repo(),
            author=self.create_author(
                name='Foo Bar',
                email='foo@example.com',
            ),
            parents=['a' * 40],
            branches=['master'],
            message='hello world',
            date_created=datetime(2013, 9, 19, 22, 15, 22),
        )
        result = serialize(revision)
        assert result['id'] == '33846695b2774b29a71795a009e8168a'
        assert result['author']['name'] == 'Foo Bar'
        assert result['author']['email'] == 'foo@example.com'
        assert result['message'] == 'hello world'
        assert result['dateCreated'] == '2013-09-19T22:15:22'
        assert result['parents'] == ['a' * 40]
        assert result['branches'] == ['master']
        assert result['external'] is None

    def test_phabricator_links(self):
        repository = self.create_repo()
        self.create_option(
            item_id=repository.id,
            name='phabricator.callsign',
            value='TEST',
        )

        revision = self.create_revision(
            sha='33846695b2774b29a71795a009e8168a',
            repository=repository,
        )
        result = serialize(revision)
        assert result['external'] == {
            'label': 'rTEST33846695b277',
            'link': 'http://phabricator.example.com/rTEST33846695b277',
        }
