from __future__ import absolute_import

import mock

from changes.config import db
from changes.constants import Status
from changes.jobs.sync_build import sync_build
from changes.models import Build, Plan, Step, BuildFamily, BuildPlan
from changes.testutils import TestCase


class SyncBuildTest(TestCase):
    @mock.patch('changes.jobs.sync_build.sync_with_builder')
    @mock.patch('changes.jobs.sync_build.queue.delay')
    @mock.patch.object(Step, 'get_implementation')
    def test_simple(self, get_implementation, queue_delay, sync_with_builder):
        implementation_cls = mock.Mock()
        implementation = implementation_cls.return_value
        get_implementation.return_value = implementation_cls

        build = self.create_build(self.project)

        plan = Plan(
            label='test',
        )
        db.session.add(plan)

        step = Step(
            plan=plan,
            implementation='test',
            order=0,
        )
        db.session.add(step)

        family = BuildFamily(
            project=build.project,
            repository=build.repository,
            revision_sha=build.revision_sha,
            label=build.label,
            author=build.author,
            target=build.target,
        )
        db.session.add(family)

        buildplan = BuildPlan(
            plan=plan,
            family=family,
            build=build,
            project=self.project,
        )
        db.session.add(buildplan)

        sync_build(build.id.hex)

        get_implementation.assert_called_once_with()

        implementation.sync.assert_called_once_with(
            build=build,
        )

        build = Build.query.get(build.id)

        assert len(sync_with_builder.mock_calls) == 0

        # ensure signal is fired
        queue_delay.assert_called_once_with('sync_build', kwargs={
            'build_id': build.id.hex,
        }, countdown=1)

    @mock.patch('changes.jobs.sync_build.sync_with_builder')
    @mock.patch('changes.jobs.sync_build.queue.delay')
    def test_without_build_plan(self, queue_delay, sync_with_builder):
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
