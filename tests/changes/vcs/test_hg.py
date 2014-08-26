from tests.changes.vcs.asserts import VcsAsserts

class MercurialVcsTest(TestCase, VcsAsserts):
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
        revisions = list(vcs.log(branch='B3'))
        assert len(revisions) == 3
        self.assertRevision(revisions[0],
                            message='3rd branch',
                            branches=['B3'])
        self.assertRevision(revisions[2],
                            message='test',
                            branches=[vcs.get_default_revision()])

        # Sanity check master
        check_call('cd %s && hg update %s' % (
            self.remote_path, vcs.get_default_revision(),
        ), shell=True)
        revisions = list(vcs.log(branch=vcs.get_default_revision()))
        assert len(revisions) == 2

        revision = vcs.log(parent='tip', limit=1).next()

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