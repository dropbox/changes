from __future__ import absolute_import

from changes.vcs.git import GitVcs
from changes.vcs.hg import MercurialVcs
from changes.models import Repository, RepositoryBackend
from changes.testutils import TestCase


class GetVcsTest(TestCase):
    def test_git(self):
        repo = Repository(
            url='http://example.com/git-repo',
            backend=RepositoryBackend.git,
        )
        result = repo.get_vcs()
        assert type(result) == GitVcs

    def test_hg(self):
        repo = Repository(
            url='http://example.com/git-repo',
            backend=RepositoryBackend.hg,
        )
        result = repo.get_vcs()
        assert type(result) == MercurialVcs

    def test_unknown(self):
        repo = Repository(
            url='http://example.com/git-repo',
            backend=RepositoryBackend.unknown,
        )
        result = repo.get_vcs()
        assert result is None
