from __future__ import absolute_import

import mock

from changes.jobs.notify_listeners import notify_revision_created
from changes.signals import revision_created
from changes.testutils import TestCase


class NotifyRevisionCreatedTest(TestCase):
    def test_simple(self):
        repo = self.create_repo()
        revision = self.create_revision(repository=repo)

        dummy_listener = mock.Mock(spec=lambda: None)
        dummy_listener.__name__ = 'dummy_listener'

        revision_created.connect(dummy_listener)

        try:
            notify_revision_created(
                repository_id=repo.id.hex,
                revision_sha=revision.sha,
            )
        finally:
            revision_created.disconnect(dummy_listener)

        dummy_listener.assert_called_once_with(revision)
