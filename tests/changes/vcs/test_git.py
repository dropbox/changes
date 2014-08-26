from __future__ import absolute_import

import os

from subprocess import check_call

from changes.testutils import TestCase
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

    def setUp(self):
        self.reset()
        self.addCleanup(check_call, 'rm -rf %s' % (self.root,), shell=True)

    def reset(self):
        check_call('rm -rf %s' % (self.root,), shell=True)
        check_call('mkdir -p %s %s' % (self.path, self.remote_path), shell=True)
        check_call('git init %s' % (self.remote_path,), shell=True)
        with open(os.path.join(self.remote_path, '.git/config'), 'w') as fp:
            fp.write('[user]\n')
            fp.write('email=foo@example.com\n')
            fp.write('name=Foo Bar\n')
        check_call('cd %s && touch FOO && git add FOO && git commit -m "test\nlol\n"' % (
            self.remote_path,
        ), shell=True)
        check_call('cd %s && touch BAR && git add BAR && git commit -m "biz\nbaz\n"' % (
            self.remote_path,
        ), shell=True)

    def get_vcs(self):
        return GitVcs(
            url=self.url,
            path=self.path
        )

    def test_get_default_revision(self):
        vcs = self.get_vcs()
        assert vcs.get_default_revision() == 'master'

    def test_log_throws_errors_when_needed(self):
        vcs = self.get_vcs()

        try:
            vcs.log(parent='HEAD', branch='master').next()
            self.fail('log passed with both branch and master specified')
        except ValueError:
            pass

    def test_log_with_branches(self):
        vcs = self.get_vcs()

        # Create another branch and move it ahead of the master branch
        check_call('cd %s && git checkout -b B2' % self.remote_path, shell=True)
        check_call('cd %s && touch BAZ && git add BAZ && git commit -m "second branch commit"' % (
            self.remote_path,
        ), shell=True)

        # Create a third branch off master with a commit not in B2
        check_call('cd %s && git checkout %s' % (
            self.remote_path, vcs.get_default_revision(),
        ), shell=True)
        check_call('cd %s && git checkout -b B3' % self.remote_path, shell=True)
        check_call('cd %s && touch IPSUM && git add IPSUM && git commit -m "3rd branch"' % (
            self.remote_path,
        ), shell=True)
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
        check_call('cd %s && git checkout %s' % (
            self.remote_path, vcs.get_default_revision(),
        ), shell=True)
        revisions = list(vcs.log(branch=vcs.get_default_revision()))
        assert len(revisions) == 2

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
        assert vcs.is_child_parent(child_in_question=revisions[0].id, parent_in_question=revisions[1].id)
        assert vcs.is_child_parent(child_in_question=revisions[1].id, parent_in_question=revisions[0].id) is False

    def test_get_known_branches(self):
        vcs = self.get_vcs()
        vcs.clone()
        vcs.update()

        branches = vcs.get_known_branches()
        self.assertEquals(1, len(branches))
        self.assertIn('master', branches)

        check_call('cd %s && git checkout -B test_branch' % self.remote_path,
                   shell=True)
        vcs.update()
        branches = vcs.get_known_branches()
        self.assertEquals(2, len(branches))
        self.assertIn('test_branch', branches)
