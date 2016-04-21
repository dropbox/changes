from __future__ import absolute_import

import pytest
import os.path

from subprocess import check_call, check_output

from changes.testutils import TestCase
from changes.vcs.base import (
        ContentReadError, UnknownChildRevision, UnknownParentRevision,
)
from changes.vcs.git import GitVcs

from tests.changes.vcs.asserts import VcsAsserts


class GitVcsTest(TestCase, VcsAsserts):
    root = '/tmp/changes-git-test'
    path = '%s/clone' % (root,)
    remote_path = '%s/remote' % (root,)
    url = 'file://%s' % (remote_path,)

    def _get_last_two_revisions(self, marker, revisions):
        if marker in revisions[0].branches:
            return revisions[0], revisions[1]
        else:
            return revisions[1], revisions[0]

    def _set_author(self, name, email, path=None):
        if not path:
            path = self.remote_path
        path = "%s/.git" % (path,)
        check_call(['git', '--git-dir', path, 'config', '--replace-all',
                   'user.name', name])
        check_call(['git', '--git-dir', path, 'config', '--replace-all',
                   'user.email', email])

    def setUp(self):
        self.reset()
        self.addCleanup(check_call, ['rm', '-rf', self.root],)

    def reset(self):
        check_call(['rm', '-rf', self.root])
        check_call(['mkdir', '-p', self.path, self.remote_path])
        check_call(['git', 'init', self.remote_path])
        self._set_author('Foo Bar', 'foo@example.com')

        self._add_file('FOO', self.remote_path, commit_msg="test\nlol\n")
        self._add_file('BAR', self.remote_path, commit_msg="biz\nbaz\n")

    def _add_file(self, filename, repo_path, commit_msg=None, content='', target=None):
        if target:
            check_output(['ln', '-s', target, filename], cwd=repo_path)
        else:
            with open(os.path.join(repo_path, filename), 'w') as f:
                f.write(content)
        check_call(['git', 'add', filename], cwd=repo_path)
        check_call(['git', 'commit', '-m', commit_msg], cwd=repo_path)

    def get_vcs(self):
        return GitVcs(
            url=self.url,
            path=self.path
        )

    def test_get_default_revision(self):
        vcs = self.get_vcs()
        assert vcs.get_default_revision() == 'master'

    def test_log_with_authors(self):
        vcs = self.get_vcs()

        # Create a commit with a new author
        self._set_author('Another Committer', 'ac@d.not.zm.exist')
        self._add_file('BAZ', self.remote_path, commit_msg="bazzy")

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

        # Create a third commit
        self._set_author('Another Committer', 'ac@d.not.zm.exist')
        self._add_file('BAZ', self.remote_path, commit_msg="bazzy")

        vcs.clone()
        vcs.update()
        revisions = list(vcs.log())
        assert len(revisions) == 3

        # one revision
        revisions = list(vcs.log(paths=["BAZ"]))
        assert len(revisions) == 1, "one path, len " + len(revisions)

        self.assertRevision(revisions[0],
                            message='bazzy')

        # multiple revisions
        revisions = list(vcs.log(paths=["FOO", "BAZ"]))
        assert len(revisions) == 2, "two paths without wildcard, len " + len(revisions)

        revisions = list(vcs.log(paths=["FO*", "BAZ"]))
        assert len(revisions) == 2, "two paths with wildcards, len " + len(revisions)

        self.assertRevision(revisions[0],
                            message='bazzy')

        self.assertRevision(revisions[1],
                            message="test\nlol\n")

        # TODO: and a different branch!

    def test_log_with_paths_and_branches(self):
        # branch is also a bare parameter in git, so let's make sure branches
        # and paths play nicely together. Not as important to test this in hg
        vcs = self.get_vcs()

        # Create another branch and move it ahead of the master branch
        check_call('git checkout -b B2'.split(' '), cwd=self.remote_path)
        self._add_file('BAZ', self.remote_path, commit_msg='second branch commit')

        # Create a third branch off master with a commit not in B2
        check_call(['git', 'checkout', vcs.get_default_revision()], cwd=self.remote_path)
        check_call('git checkout -b B3'.split(' '), cwd=self.remote_path)
        self._add_file('IPSUM', self.remote_path, commit_msg='3rd branch')

        vcs.clone()
        vcs.update()

        # Ensure git log normally includes commits from all branches
        revisions = list(vcs.log())
        assert len(revisions) == 4

        # While in B3, do a git log on B2. FOO and BAZ should show up, but not
        # IPSUM
        revisions = list(vcs.log(branch='B2', paths=["FOO", "BAZ", "IPSUM"]))
        assert len(revisions) == 2

        # Sanity check master
        check_call(['git', 'checkout', vcs.get_default_revision()], cwd=self.remote_path)
        revisions = list(vcs.log(branch=vcs.get_default_revision()))
        assert len(revisions) == 2

    def test_log_with_branches(self):
        vcs = self.get_vcs()

        # Create another branch and move it ahead of the master branch
        check_call('git checkout -b B2'.split(' '), cwd=self.remote_path)
        self._add_file('BAZ', self.remote_path, commit_msg='second branch commit')

        # Create a third branch off master with a commit not in B2
        check_call(['git', 'checkout', vcs.get_default_revision()], cwd=self.remote_path)
        check_call('git checkout -b B3'.split(' '), cwd=self.remote_path)
        self._add_file('IPSUM', self.remote_path, commit_msg='3rd branch')

        vcs.clone()
        vcs.update()

        # Ensure git log normally includes commits from all branches
        revisions = list(vcs.log())
        assert len(revisions) == 4

        # Git timestamps are only accurate to the second. But since this test
        #   creates these commits so close to each other, there's a race
        #   condition here. Ultimately, we only care that both commits appear
        #   last in the log, so allow them to be out of order.
        last_rev, previous_rev = self._get_last_two_revisions('B3', revisions)
        self.assertRevision(last_rev,
                            message='3rd branch',
                            branches=['B3'])
        self.assertRevision(previous_rev,
                            message='second branch commit',
                            branches=['B2'])

        # Note that the list of branches here differs from the hg version
        #   because hg only returns the branch name from the changeset, which
        #   does not include any ancestors.
        self.assertRevision(revisions[3],
                            message='test',
                            branches=[vcs.get_default_revision(), 'B2', 'B3'])

        # Ensure git log with B3 only
        revisions = list(vcs.log(branch='B3'))
        assert len(revisions) == 3
        self.assertRevision(revisions[0],
                            message='3rd branch',
                            branches=['B3'])
        self.assertRevision(revisions[2],
                            message='test',
                            branches=[vcs.get_default_revision(), 'B2', 'B3'])

        # Sanity check master
        check_call(['git', 'checkout', vcs.get_default_revision()], cwd=self.remote_path)
        revisions = list(vcs.log(branch=vcs.get_default_revision()))
        assert len(revisions) == 2

    def test_first_parent(self):
        vcs = self.get_vcs()

        self._add_file('BAZ', self.remote_path, commit_msg='baz')
        self._add_file('BAZ2', self.remote_path, commit_msg='baz2')

        # Create the commit that will be the second parent.
        check_call(['git', 'checkout', 'HEAD^'], cwd=self.remote_path)
        self._add_file('SECOND_PARENT', self.remote_path, commit_msg='second parent')
        to_merge = check_output(['git', 'rev-parse', 'HEAD'], cwd=self.remote_path)

        # Merge commit into master.
        check_call('git checkout master'.split(' '), cwd=self.remote_path)
        check_call(['git', 'merge', to_merge.strip('\n')], cwd=self.remote_path)

        vcs.clone()
        vcs.update()
        revisions = list(vcs.log())
        assert len(revisions) == 5
        revisions = list(vcs.log(first_parent=False))
        assert len(revisions) == 6

    def test_log_throws_errors_when_needed(self):
        vcs = self.get_vcs()

        try:
            vcs.log(parent='HEAD', branch='master').next()
            self.fail('log passed with both branch and master specified')
        except ValueError:
            pass

    def test_simple(self):
        vcs = self.get_vcs()
        vcs.clone()
        vcs.update()
        revision = vcs.log(parent='HEAD', limit=1).next()
        assert len(revision.id) == 40
        self.assertRevision(revision,
                            author='Foo Bar <foo@example.com>',
                            message='biz\nbaz\n',
                            subject='biz')
        revisions = list(vcs.log())
        assert len(revisions) == 2
        assert revisions[0].subject == 'biz'
        assert revisions[0].message == 'biz\nbaz\n'
        assert revisions[0].author == 'Foo Bar <foo@example.com>'
        assert revisions[0].committer == 'Foo Bar <foo@example.com>'
        assert revisions[0].parents == [revisions[1].id]
        assert revisions[0].author_date == revisions[0].committer_date is not None
        assert revisions[0].branches == ['master']
        assert revisions[1].subject == 'test'
        assert revisions[1].message == 'test\nlol\n'
        assert revisions[1].author == 'Foo Bar <foo@example.com>'
        assert revisions[1].committer == 'Foo Bar <foo@example.com>'
        assert revisions[1].parents == []
        assert revisions[1].author_date == revisions[1].committer_date is not None
        assert revisions[1].branches == ['master']
        diff = vcs.export(revisions[0].id)
        assert diff == """diff --git a/BAR b/BAR
new file mode 100644
index 0000000..e69de29
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
        assert not vcs.is_child_parent(child_in_question=revisions[1].id,
                                       parent_in_question=revisions[0].id)

        unknown_sha = 'ffffffffffffffffffffffffffffffffffffffff'
        with pytest.raises(UnknownChildRevision):
            vcs.is_child_parent(child_in_question=unknown_sha,
                                parent_in_question=revisions[1].id)
        with pytest.raises(UnknownParentRevision):
            vcs.is_child_parent(child_in_question=revisions[1].id,
                                parent_in_question=unknown_sha)

    def test_get_known_branches(self):
        vcs = self.get_vcs()
        vcs.clone()
        vcs.update()

        branches = vcs.get_known_branches()
        self.assertEquals(1, len(branches))
        self.assertIn('master', branches)

        check_call('git checkout -B test_branch'.split(), cwd=self.remote_path)
        vcs.update()
        branches = vcs.get_known_branches()
        self.assertEquals(2, len(branches))
        self.assertIn('test_branch', branches)

    def test_update_repo_url(self):
        # Create a second remote
        remote_path2 = '%s/remote2/' % (self.root,)
        check_call(['mkdir', '-p', remote_path2])
        check_call(['git', 'clone', self.remote_path, remote_path2], cwd=self.root)
        self._set_author('Remote2 Committer', 'Remote2Committer@example.com', path=remote_path2)
        self._add_file('BAZ', remote_path2, commit_msg='bazzy')

        # Clone original remote
        vcs = self.get_vcs()
        vcs.clone()
        vcs.update()
        revisions = list(vcs.log())
        assert len(revisions) == 2

        # Update to new remote
        vcs.url = remote_path2
        vcs.update()
        revisions = list(vcs.log())
        assert len(revisions) == 3

        # Revert to original
        vcs.url = self.remote_path
        vcs.update()
        revisions = list(vcs.log())
        assert len(revisions) == 2

    def test_read_file(self):
        vcs = self.get_vcs()
        vcs.clone()
        vcs.update()

        # simple case
        assert vcs.read_file('HEAD', 'FOO') == ''

        # unknown file
        with pytest.raises(ContentReadError):
            vcs.read_file('HEAD', 'doesnotexist')

        # unknown sha
        with pytest.raises(ContentReadError):
            vcs.read_file('a' * 40, 'FOO')

    def test_read_file_symlink(self):
        content = 'Line 1\nLine 2\n'
        self._add_file('REAL', self.remote_path, content=content, commit_msg='Target file.')
        self._add_file('INDIRECT', self.remote_path, target='REAL', commit_msg="Here we go.")
        vcs = self.get_vcs()
        vcs.clone()
        vcs.update()

        assert vcs.read_file('HEAD', 'INDIRECT') == content

        with pytest.raises(ContentReadError):
            vcs.read_file('HEAD', 'does_not_exist.txt')

    def test_read_file_symlink_out_of_tree(self):
        oot = os.path.join(self.root, 'out_of_tree.txt')
        with open(oot, 'w') as f:
            f.write("Out of tree!\n")
        self._add_file('INDIRECT', self.remote_path, target=oot, commit_msg="Here we go.")
        vcs = self.get_vcs()
        vcs.clone()
        vcs.update()

        with pytest.raises(ContentReadError):
            vcs.read_file('HEAD', 'INDIRECT')

    def test_read_file_with_diff(self):
        PATCH = """diff --git a/FOO b/FOO
index e69de29..d0c77a5 100644
--- a/FOO
+++ b/FOO
@@ -0,0 +1 @@
+blah
diff --git a/FOO1 b/FOO1
index e69de29..d0c77a5 100644
--- a/FOO1
+++ b/FOO1
@@ -1,1 +1 @@
-blah
+blah
"""
        vcs = self.get_vcs()
        vcs.clone()
        vcs.update()

        assert vcs.read_file('HEAD', 'FOO', diff=PATCH) == 'blah\n'
