from __future__ import absolute_import

import os

from subprocess import check_call

from changes.testutils import TestCase
from changes.vcs.git import GitVcs


class GitVcsTest(TestCase):
    root = '/tmp/changes-git-test'
    path = '%s/clone' % (root,)
    remote_path = '%s/remote' % (root,)
    url = 'file://%s' % (remote_path,)

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

    def test_simple(self):
        vcs = self.get_vcs()
        vcs.clone()
        vcs.update()
        revision = vcs.get_revision('HEAD')
        assert len(revision.id) == 40
        assert revision.message == 'biz\nbaz\n'
        assert revision.subject == 'biz'
        assert revision.author == 'Foo Bar <foo@example.com>'
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
