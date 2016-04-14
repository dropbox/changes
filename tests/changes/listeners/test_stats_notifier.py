from __future__ import absolute_import

from changes.constants import Result
from changes.testutils import TestCase

from changes.listeners.stats_notifier import (
        build_finished_metrics,
)


class StatsNotifierTest(TestCase):

    def test_build_finished(self):
        project = self.create_project(name='test', slug='silly:slug')

        def get_metrics(result, tags=['commit']):
            return build_finished_metrics(
                self.create_build(project, tags=tags, result=result).id)

        self.assertEquals(get_metrics(Result.aborted),
                          [])
        self.assertEquals(get_metrics(Result.passed),
                          ['build_complete_commit_silly_slug'])
        self.assertEquals(get_metrics(Result.failed),
                          ['build_complete_commit_silly_slug', 'build_failed_commit_silly_slug'])
        self.assertEquals(get_metrics(Result.infra_failed),
                          ['build_complete_commit_silly_slug', 'build_failed_commit_silly_slug'])

        self.assertEquals(get_metrics(Result.passed, tags=None),
                          [])
        self.assertEquals(get_metrics(Result.passed, tags=[]),
                          [])
        self.assertEquals(get_metrics(Result.passed, tags=['commit-queue']),
                          [])
