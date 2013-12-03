from datetime import datetime

from changes.models import Revision
from changes.vcs.base import RevisionResult
from changes.testutils.cases import TestCase


class RevisionResultTestCase(TestCase):
    def test_simple(self):
        repo = self.create_repo()
        result = RevisionResult(
            id='c' * 40,
            author='Foo Bar <foo@example.com>',
            committer='Biz Baz <baz@example.com>',
            author_date=datetime(2013, 9, 19, 22, 15, 22),
            committer_date=datetime(2013, 9, 19, 22, 15, 23),
            message='Hello world!',
            parents=['a' * 40, 'b' * 40],

        )
        revision, created = result.save(repo)

        assert created

        assert type(revision) == Revision
        assert revision.repository.id == repo.id
        assert revision.sha == 'c' * 40
        assert revision.message == 'Hello world!'
        assert revision.author.name == 'Foo Bar'
        assert revision.author.email == 'foo@example.com'
        assert revision.committer.name == 'Biz Baz'
        assert revision.committer.email == 'baz@example.com'
        assert revision.parents == ['a' * 40, 'b' * 40]
        assert revision.date_created == datetime(2013, 9, 19, 22, 15, 22)
        assert revision.date_committed == datetime(2013, 9, 19, 22, 15, 23)
