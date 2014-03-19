from __future__ import absolute_import

import os

from datetime import datetime
from subprocess import check_call

from changes.testutils import TestCase
from changes.vcs.hg import MercurialVcs


class MercurialVcsTest(TestCase):
    root = '/tmp/changes-hg-test'
    path = '%s/clone' % (root,)
    remote_path = '%s/remote' % (root,)
    url = 'file://%s' % (remote_path,)

    def setUp(self):
        self.reset()
        self.addCleanup(check_call, 'rm -rf %s' % (self.root,), shell=True)

    def reset(self):
        check_call('rm -rf %s' % (self.root,), shell=True)
        check_call('mkdir -p %s %s' % (self.path, self.remote_path), shell=True)
        check_call('hg init %s' % (self.remote_path,), shell=True)
        with open(os.path.join(self.remote_path, '.hg/hgrc'), 'w') as fp:
            fp.write('[ui]\n')
            fp.write('username=Foo Bar <foo@example.com>\n')
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

    def test_simple(self):
        vcs = self.get_vcs()
        vcs.clone()
        vcs.update()
        revision = vcs.get_revision('tip')
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
