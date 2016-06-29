from __future__ import absolute_import

import os
import pytest

from datetime import datetime
from subprocess import check_call

from changes.testutils import TestCase
from changes.vcs.base import CommandError, UnknownRevision
from changes.vcs.hg import MercurialVcs

from tests.changes.vcs.asserts import VcsAsserts


def has_current_hg_version():
    import pkg_resources

    try:
        mercurial = pkg_resources.get_distribution('mercurial')
    except pkg_resources.DistributionNotFound:
        return False

    return mercurial.parsed_version >= pkg_resources.parse_version('2.4')


@pytest.mark.skipif(not has_current_hg_version(),
                    reason='missing or invalid mercurial version')
class MercurialVcsTest(TestCase, VcsAsserts):
    root = '/tmp/changes-hg-test'
    path = '%s/clone' % (root,)
    remote_path = '%s/remote' % (root,)
    url = 'file://%s' % (remote_path,)

    def _set_author(self, author):
        with open(os.path.join(self.remote_path, '.hg/hgrc'), 'w') as fp:
            fp.write('[ui]\n')
            fp.write('username={0}\n'.format(author))

    def setUp(self):
        self.reset()
        self.addCleanup(check_call, 'rm -rf %s' % (self.root,), shell=True)

    def reset(self):
        check_call('rm -rf %s' % (self.root,), shell=True)
        check_call('mkdir -p %s %s' % (self.path, self.remote_path), shell=True)
        check_call('hg init %s' % (self.remote_path,), shell=True)
        self._set_author('Foo Bar <foo@example.com>')
        check_call('cd %s && touch FOO && hg add FOO && hg commit -m "test\nlol"' % (
            self.remote_path,
        ), shell=True)
        check_call('cd %s && touch BAR && hg add BAR && hg commit -m "biz\nbaz"' % (
            self.remote_path,
        ), shell=True)

    def get_vcs(self):
        return MercurialVcs(
            url=self.url,
            path=self.path
        )

    def test_get_default_revision(self):
        vcs = self.get_vcs()
        assert vcs.get_default_revision() == 'default'

    def test_log_with_authors(self):
        vcs = self.get_vcs()

        # Create a commit with a new author
        self._set_author('Another Committer <ac@d.not.zm.exist>')
        check_call('cd %s && touch BAZ && hg add BAZ && hg commit -m "bazzy"' % (
            self.remote_path,
        ), shell=True)
        vcs.clone()
        vcs.update()
        revisions = list(vcs.log())
        assert len(revisions) == 3

        revisions = list(vcs.log(author='Another Committer'))
        assert len(revisions) == 1
        self.assertRevision(revisions[0],
                            author='Another Committer <ac@d.not.zm.exist>',
                            message='bazzy')

        revisions = list(vcs.log(author='ac@d.not.zm.exist'))
        assert len(revisions) == 1
        self.assertRevision(revisions[0],
                            author='Another Committer <ac@d.not.zm.exist>',
                            message='bazzy')

        revisions = list(vcs.log(branch=vcs.get_default_revision(),
                                 author='Foo'))
        assert len(revisions) == 2

    def test_log_with_paths(self):
        vcs = self.get_vcs()

        # Create a commit with a new author
        self._set_author('Another Committer <ac@d.not.zm.exist>')
        check_call('cd %s && touch BAZ && hg add BAZ && hg commit -m "bazzy"' % (
            self.remote_path,
        ), shell=True)
        vcs.clone()
        vcs.update()
        revisions = list(vcs.log())
        assert len(revisions) == 3

        revisions = list(vcs.log(paths=["FOO"]))
        assert len(revisions) == 1
        self.assertRevision(revisions[0],
                            message='test\nlol')

        revisions = list(vcs.log(paths=["FOO", "BAZ"]))
        assert len(revisions) == 2
        self.assertRevision(revisions[0],
                            message='bazzy')

        self.assertRevision(revisions[1],
                            message='test\nlol')

        revisions = list(vcs.log(paths=["FO*", "BAZ"]))
        assert len(revisions) == 2
        self.assertRevision(revisions[0],
                            message='bazzy')

        self.assertRevision(revisions[1],
                            message='test\nlol')

    def test_log_throws_errors_when_needed(self):
        vcs = self.get_vcs()

        try:
            vcs.log(parent='tip', branch='default').next()
            self.fail('log passed with both branch and master specified')
        except ValueError:
            pass

    def test_log_with_branches(self):
        vcs = self.get_vcs()

        # Create another branch and move it ahead of the master branch
        check_call('cd %s && hg branch B2' % self.remote_path, shell=True)
        check_call('cd %s && touch BAZ && hg add BAZ && hg commit -m "second branch commit"' % (
            self.remote_path,
        ), shell=True)

        # Create a third branch off master with a commit not in B2
        check_call('cd %s && hg update %s' % (
            self.remote_path, vcs.get_default_revision(),
        ), shell=True)
        check_call('cd %s && hg branch B3' % self.remote_path, shell=True)
        check_call('cd %s && touch IPSUM && hg add IPSUM && hg commit -m "3rd branch"' % (
            self.remote_path,
        ), shell=True)
        vcs.clone()
        vcs.update()

        # Ensure git log normally includes commits from all branches
        revisions = list(vcs.log())
        assert len(revisions) == 4
        self.assertRevision(revisions[0],
                            message='3rd branch',
                            branches=['B3'])
        self.assertRevision(revisions[1],
                            message='second branch commit',
                            branches=['B2'])

        # Note that the list of branches here differs from the git version
        #   because git returns all the ancestor branch names as well.
        self.assertRevision(revisions[3],
                            message='test',
                            branches=[vcs.get_default_revision()])

        # Ensure git log with B3 only
        # XXX: in mercurial it *does not* show ancestor commits
        revisions = list(vcs.log(branch='B3'))
        assert len(revisions) == 1
        self.assertRevision(revisions[0],
                            message='3rd branch',
                            branches=['B3'])

        # Sanity check master
        check_call('cd %s && hg update %s' % (
            self.remote_path, vcs.get_default_revision(),
        ), shell=True)
        revisions = list(vcs.log(branch=vcs.get_default_revision()))
        assert len(revisions) == 2

    def test_simple(self):
        vcs = self.get_vcs()
        vcs.clone()
        vcs.update()
        revision = vcs.log(parent='tip', limit=1).next()
        assert len(revision.id) == 40
        assert revision.message == 'biz\nbaz'
        assert revision.subject == 'biz'
        assert revision.author == 'Foo Bar <foo@example.com>'
        revisions = list(vcs.log())
        assert len(revisions) == 2
        assert revisions[0].subject == 'biz'
        assert revisions[0].message == 'biz\nbaz'
        assert revisions[0].author == 'Foo Bar <foo@example.com>'
        assert revisions[0].committer == 'Foo Bar <foo@example.com>'
        assert revisions[0].parents == [revisions[1].id]
        assert type(revisions[0].author_date) is datetime
        assert revisions[0].author_date == revisions[0].committer_date is not None
        assert revisions[0].branches == ['default']
        assert revisions[1].subject == 'test'
        assert revisions[1].message == 'test\nlol'
        assert revisions[1].author == 'Foo Bar <foo@example.com>'
        assert revisions[1].committer == 'Foo Bar <foo@example.com>'
        assert revisions[1].parents == []
        assert revisions[1].author_date == revisions[1].committer_date is not None
        assert revisions[1].branches == ['default']
        diff = vcs.export(revisions[0].id)
        assert diff == """diff --git a/BAR b/BAR
new file mode 100644
"""
        assert vcs.get_changed_files(revisions[0].id) == set(["BAR"])
        revisions = list(vcs.log(offset=0, limit=1))
        assert len(revisions) == 1
        assert revisions[0].subject == 'biz'

        revisions = list(vcs.log(offset=1, limit=1))
        assert len(revisions) == 1
        assert revisions[0].subject == 'test'

    def test_is_child_parent(self):
        vcs = self.get_vcs()
        vcs.clone()
        vcs.update()
        revisions = list(vcs.log())
        assert vcs.is_child_parent(child_in_question=revisions[0].id,
                                   parent_in_question=revisions[1].id)
        assert vcs.is_child_parent(child_in_question=revisions[1].id,
                                   parent_in_question=revisions[0].id) is False

    def test_get_known_branches(self):
        vcs = self.get_vcs()
        vcs.clone()
        vcs.update()

        branches = vcs.get_known_branches()
        self.assertEquals(1, len(branches))
        self.assertIn('default', branches)

        check_call(('cd %s && hg branch test_branch && hg ci -m "New branch"'
                    % self.remote_path),
                   shell=True)
        vcs.update()
        branches = vcs.get_known_branches()
        self.assertEquals(2, len(branches))
        self.assertIn('test_branch', branches)

    def test_export_unknown_revision(self):
        vcs = self.get_vcs()
        vcs.clone()
        vcs.update()
        with self.assertRaises(UnknownRevision):
            vcs.export('4444444444444444444444444444444444444444')

    def test_read_file(self):
        vcs = self.get_vcs()
        vcs.clone()
        vcs.update()

        sha = vcs.run(['id', '-i']).strip()

        # simple case
        assert vcs.read_file(sha, 'FOO') == ''

        # unknown file
        with pytest.raises(CommandError):
            vcs.read_file(sha, 'doesnotexist')

        # unknown sha
        with pytest.raises(CommandError):
            vcs.read_file('a' * 40, 'FOO')

    def test_read_file_with_diff(self):
        PATCH = """diff -r 2104491cf7a3 FOO
--- a/FOO Mon Aug 10 13:49:52 2015 -0700
+++ b/FOO Mon Aug 10 16:23:11 2015 -0700
@@ -0,0 +1,1 @@
+blah
diff -r 2104491cf7a3 FOO1
--- a/FOO1 Mon Aug 10 13:49:52 2015 -0700
+++ b/FOO1 Mon Aug 10 16:23:11 2015 -0700
@@ -1,1 +1,1 @@
-blah
+blah
"""
        vcs = self.get_vcs()
        vcs.clone()
        vcs.update()

        sha = vcs.run(['id', '-i']).strip()

        assert vcs.read_file(sha, 'FOO', diff=PATCH) == 'blah\n'
