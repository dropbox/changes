from datetime import datetime

import pytest

from changes.models.revision import Revision
from changes.testutils.cases import TestCase
from changes.vcs.base import InvalidDiffError, RevisionResult, Vcs


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
