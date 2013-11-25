from __future__ import absolute_import

import mock

from changes.constants import Status
from changes.jobs.sync_build import sync_build
from changes.models import Build
from changes.testutils import TestCase


class SyncBuildTest(TestCase):
    @mock.patch('changes.jobs.sync_build.sync_with_builder')
    @mock.patch('changes.jobs.sync_build.queue.delay')
    def test_simple(self, queue_delay, sync_with_builder):
        def mark_finished(build):
            build.status = Status.finished

        sync_with_builder.side_effect = mark_finished

        build = self.create_build(self.project)

        sync_build(build.id.hex)

        build = Build.query.get(build.id)

        assert build.status == Status.finished

        # build sync is abstracted via sync_with_builder
        sync_with_builder.assert_called_once_with(build)

        # ensure signal is fired
        queue_delay.assert_called_once_with('notify_listeners', kwargs={
            'build_id': build.id.hex,
            'signal_name': 'build.finished',
        })
