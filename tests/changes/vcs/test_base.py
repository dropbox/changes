from datetime import datetime

import pytest

import mock

from changes.models.revision import Revision
from changes.models.repository import RepositoryBackend
from changes.testutils.cases import TestCase
from changes.vcs.base import InvalidDiffError, RevisionResult, Vcs


class RevisionResultTestCase(TestCase):
    def test_simple_git(self):
        repo = self.create_repo(backend=RepositoryBackend.git)
        result = RevisionResult(
            id='c' * 40,
            author='Foo Bar <foo@example.com>',
            committer='Biz Baz <baz@example.com>',
            author_date=datetime(2013, 9, 19, 22, 15, 22),
            committer_date=datetime(2013, 9, 19, 22, 15, 23),
            message='Hello world!',
            parents=['a' * 40, 'b' * 40],
        )
        revision, created, _ = result.save(repo)

        assert created

        assert type(revision) == Revision
        assert revision.repository == repo
        assert revision.sha == 'c' * 40
        assert revision.message == 'Hello world!'
        assert revision.author.name == 'Foo Bar'
        assert revision.author.email == 'foo@example.com'
        assert revision.committer.name == 'Biz Baz'
        assert revision.committer.email == 'baz@example.com'
        assert revision.parents == ['a' * 40, 'b' * 40]
        assert revision.date_created == datetime(2013, 9, 19, 22, 15, 22)
        assert revision.date_committed == datetime(2013, 9, 19, 22, 15, 23)
        assert revision.patch_hash is not None

    def test_simple_hg(self):
        repo = self.create_repo(backend=RepositoryBackend.hg)
        result = RevisionResult(
            id='c' * 40,
            author='Foo Bar <foo@example.com>',
            committer='Biz Baz <baz@example.com>',
            author_date=datetime(2013, 9, 19, 22, 15, 22),
            committer_date=datetime(2013, 9, 19, 22, 15, 23),
            message='Hello world!',
            parents=['a' * 40, 'b' * 40],
        )
        revision, created, _ = result.save(repo)

        assert created

        assert type(revision) == Revision
        assert revision.repository == repo
        assert revision.sha == 'c' * 40
        assert revision.message == 'Hello world!'
        assert revision.author.name == 'Foo Bar'
        assert revision.author.email == 'foo@example.com'
        assert revision.committer.name == 'Biz Baz'
        assert revision.committer.email == 'baz@example.com'
        assert revision.parents == ['a' * 40, 'b' * 40]
        assert revision.date_created == datetime(2013, 9, 19, 22, 15, 22)
        assert revision.date_committed == datetime(2013, 9, 19, 22, 15, 23)
        assert revision.patch_hash is None

    def test_none_vcs(self):
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
        revision, created, _ = result.save(repo)

        assert created

        assert type(revision) == Revision
        assert revision.repository == repo
        assert revision.sha == 'c' * 40
        assert revision.message == 'Hello world!'
        assert revision.author.name == 'Foo Bar'
        assert revision.author.email == 'foo@example.com'
        assert revision.committer.name == 'Biz Baz'
        assert revision.committer.email == 'baz@example.com'
        assert revision.parents == ['a' * 40, 'b' * 40]
        assert revision.date_created == datetime(2013, 9, 19, 22, 15, 22)
        assert revision.date_committed == datetime(2013, 9, 19, 22, 15, 23)
        assert revision.patch_hash is None

    def test_save_again(self):
        mock_vcs = mock.MagicMock(spec=Vcs)

        repo = self.create_repo(backend=RepositoryBackend.git)
        with mock.patch.object(repo, 'get_vcs') as mock_get_vcs:
            mock_get_vcs.return_value = mock_vcs
            mock_vcs.get_patch_hash.return_value = 'a' * 40

            result = RevisionResult(
                id='c' * 40,
                author='Foo Bar <foo@example.com>',
                committer='Biz Baz <baz@example.com>',
                author_date=datetime(2013, 9, 19, 22, 15, 22),
                committer_date=datetime(2013, 9, 19, 22, 15, 23),
                message='Hello world!',
                parents=['a' * 40, 'b' * 40],
            )

            revision1, created1, _ = result.save(repo)
            revision2, created2, _ = result.save(repo)

            assert type(revision1) == type(revision2) == Revision
            assert revision1.repository == revision2.repository == repo
            assert revision1.sha == revision2.sha == 'c' * 40
            assert revision1.message == revision2.message == 'Hello world!'
            assert revision1.author.name == revision2.author.name == 'Foo Bar'
            assert revision1.author.email == revision2.author.email == 'foo@example.com'
            assert revision1.committer.name == revision2.committer.name == 'Biz Baz'
            assert revision1.committer.email == revision2.committer.email == 'baz@example.com'
            assert revision1.parents == revision2.parents == ['a' * 40, 'b' * 40]
            assert revision1.date_created == revision2.date_created == datetime(2013, 9, 19, 22, 15, 22)
            assert revision1.date_committed == revision2.date_committed == datetime(2013, 9, 19, 22, 15, 23)
            assert revision1.patch_hash == revision2.patch_hash == 'a' * 40

            assert mock_vcs.get_patch_hash.called_once_with('c' * 40)
            assert created1
            assert not created2


class SelectivelyApplyDiffTest(TestCase):
    PATCH_TEMPLATE = """diff --git a/{path} b/{path}
index e69de29..d0c77a5 100644
--- a/{path}
+++ b/{path}
@@ -1,1 +1 @@
-FOO
+blah
diff --git a/FOO1 b/FOO1
index e69de29..d0c77a5 100644
--- a/FOO1
+++ b/FOO1
@@ -1,1 +1 @@
-blah
+blah
"""

    BAD_PATCH_TEMPLATE = """diff --git a/{path} b/{path}
index e69de29..d0c77a5 100644
--- a/{path}
+++ b/{path}
@@ -0,0 +1 @@
-FOO
+blah
diff --git a/FOO1 b/FOO1
index e69de29..d0c77a5 100644
--- a/FOO1
+++ b/FOO1
@@ -1,1 +1 @@
-blah
+blah
"""

    PATCH_TEMPLATE_NO_NEWLINE_SOURCE = """diff --git a/{path} b/{path}
index e69de29..d0c77a5 100644
--- a/{path}
+++ b/{path}
@@ -1 +1 @@
-FOO
\ No newline at end of file
+blah
diff --git a/FOO1 b/FOO1
index e69de29..d0c77a5 100644
--- a/FOO1
+++ b/FOO1
@@ -1,1 +1 @@
-blah
+blah
"""

    PATCH_TEMPLATE_NO_NEWLINE_TARGET = """diff --git a/{path} b/{path}
index e69de29..d0c77a5 100644
--- a/{path}
+++ b/{path}
@@ -1 +1 @@
-FOO
+blah
\ No newline at end of file
diff --git a/FOO1 b/FOO1
index e69de29..d0c77a5 100644
--- a/FOO1
+++ b/FOO1
@@ -1,1 +1 @@
-blah
+blah
"""

    PATCH_TEMPLATE_NO_NEWLINE_BOTH = """diff --git a/{path} b/{path}
index e69de29..d0c77a5 100644
--- a/{path}
+++ b/{path}
@@ -1 +1 @@
-FOO
\ No newline at end of file
+blah
\ No newline at end of file
diff --git a/FOO1 b/FOO1
index e69de29..d0c77a5 100644
--- a/FOO1
+++ b/FOO1
@@ -1,1 +1 @@
-blah
+blah
"""

    def setUp(self):
        self.vcs = Vcs(None, None)

    def test_simple(self):
        path = 'a.txt'
        patch = self.PATCH_TEMPLATE.format(path=path)
        content = self.vcs._selectively_apply_diff(path, 'FOO\n', diff=patch)
        assert content == 'blah\n'

    def test_nested(self):
        path = 'testing/a/b/c/a.txt'
        patch = self.PATCH_TEMPLATE.format(path=path)
        content = self.vcs._selectively_apply_diff(path, 'FOO\n', diff=patch)
        assert content == 'blah\n'

    def test_untouched(self):
        path = 'a.txt'
        patch = self.PATCH_TEMPLATE.format(path='b.txt')
        content = self.vcs._selectively_apply_diff(path, 'FOO\n', diff=patch)
        assert content == 'FOO\n'

    def test_invalid_diff(self):
        path = 'a.txt'
        patch = self.BAD_PATCH_TEMPLATE.format(path=path)
        with pytest.raises(InvalidDiffError):
            self.vcs._selectively_apply_diff(path, 'FOO\n', diff=patch)

    def test_no_newline_source(self):
        path = 'a.txt'
        patch = self.PATCH_TEMPLATE_NO_NEWLINE_SOURCE.format(path=path)
        content = self.vcs._selectively_apply_diff(path, 'FOO', diff=patch)
        assert content == 'blah\n'

    def test_no_newline_target(self):
        path = 'a.txt'
        patch = self.PATCH_TEMPLATE_NO_NEWLINE_TARGET.format(path=path)
        content = self.vcs._selectively_apply_diff(path, 'FOO\n', diff=patch)
        assert content == 'blah'

    def test_no_newline_both(self):
        path = 'a.txt'
        patch = self.PATCH_TEMPLATE_NO_NEWLINE_BOTH.format(path=path)
        content = self.vcs._selectively_apply_diff(path, 'FOO', diff=patch)
        assert content == 'blah'


class GetRepositoryTestCase(TestCase):

    def test_correct(self):
        for (url, expected_name) in [
            ('example.com:test.git', 'test.git'),
            ('example.com:test', 'test'),
            ('ssh@example.com:test', 'test'),
            ('example.com:prefix/test', 'test'),
            ('example.com:test-with-hyphen', 'test-with-hyphen'),
            ('example.com:some-prefix/test-with-hyphen', 'test-with-hyphen'),
        ]:
            assert Vcs.get_repository_name(url) == expected_name
