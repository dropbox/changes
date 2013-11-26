from __future__ import absolute_import

import os

from changes.testutils import TestCase
from changes.vcs.git import GitVcs


class GitVcsTest(TestCase):
    root = '/tmp/changes-git-test'
    path = '%s/clone' % (root,)
    remote_path = '%s/remote' % (root,)
    url = 'file://%s' % (remote_path,)

    def setUp(self):
        self.reset()
        self.addCleanup(self.reset)

    def reset(self):
        os.system('rm -rf %s' % (self.root,))
        os.system('mkdir -p %s %s' % (self.path, self.remote_path))
        os.system('git init %s' % (self.remote_path,))
        with open(os.path.join(self.remote_path, '.git/config'), 'w') as fp:
            fp.write('[user]\n')
            fp.write('email=foo@example.com\n')
            fp.write('name=Foo Bar\n')
        os.system('cd %s && touch FOO && git add FOO && git commit -m "test\nlol\n"' % (
            self.remote_path,
        ))

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
        assert revision.message == 'test\nlol\n'
        assert revision.subject == 'test'
        assert revision.author == 'Foo Bar <foo@example.com>'
