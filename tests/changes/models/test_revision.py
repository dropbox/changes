from __future__ import absolute_import

import pytest

from sqlalchemy.orm.exc import MultipleResultsFound

from changes.models.repository import Repository, RepositoryBackend
from changes.models.revision import Revision
from changes.testutils import TestCase


class RevisionTest(TestCase):
    sha = '73a5e15bc8a67024ba0d989d28731605ad83144c'
    sha_similiar = '73a5e15bc8a67024ba0d989d28731605ad83144d'

    def _create_repository(self):
        return Repository(
            url='http://example.com/git-repo',
            backend=RepositoryBackend.git,
        )

    def test_prefix_prefix(self):
        repository = self._create_repository()
        revision = self.create_revision(repository=repository, sha=self.sha)
        assert Revision.get_by_sha_prefix_query(repository.id, '73a5').scalar() == revision

    def test_prefix_full(self):
        repository = self._create_repository()
        revision = self.create_revision(repository=repository, sha=self.sha)
        assert Revision.get_by_sha_prefix_query(repository.id, self.sha).scalar() == revision

    def test_prefix_ambiguous(self):
        repository = self._create_repository()
        revision_1 = self.create_revision(repository=repository, sha=self.sha)
        revision_2 = self.create_revision(repository=repository, sha=self.sha_similiar)
        with pytest.raises(MultipleResultsFound):
            Revision.get_by_sha_prefix_query(repository.id, '73a5').scalar()
