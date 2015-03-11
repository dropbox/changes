from __future__ import absolute_import

from datetime import datetime

from flask import current_app
import mock

from changes.constants import Result
from changes.testutils import TestCase
from changes.listeners.analytics_notifier import build_finished_handler


class AnalyticsNotifierTest(TestCase):

    def setUp(self):
        super(AnalyticsNotifierTest, self).setUp()

    def _set_config_url(self, url):
        current_app.config['ANALYTICS_POST_URL'] = url

    @mock.patch('changes.listeners.analytics_notifier.post_build_data')
    def test_no_url(self, post_fn):
        self._set_config_url(None)
        project = self.create_project(name='test', slug='test')
        build = self.create_build(project, result=Result.failed)
        build_finished_handler(build_id=build.id.hex)
        self.assertEquals(post_fn.call_count, 0)

    @mock.patch('changes.listeners.analytics_notifier.post_build_data')
    def test_failed_build(self, post_fn):
        URL = "https://analytics.example.com/report?source=changes"
        self._set_config_url(URL)
        project = self.create_project(name='test', slug='project-slug')
        self.assertEquals(post_fn.call_count, 0)
        duration = 1234
        created = 1424998888
        started = created + 10
        finished = started + duration

        def ts_to_datetime(ts):
            return datetime.utcfromtimestamp(ts)

        build = self.create_build(project, result=Result.failed, target='D1',
                                  label='Some sweet diff', duration=duration,
                                  date_created=ts_to_datetime(created), date_started=ts_to_datetime(started),
                                  date_finished=ts_to_datetime(finished))
        build_finished_handler(build_id=build.id.hex)

        expected_data = {
            'build_id': build.id.hex,
            'number': 1,
            'target': 'D1',
            'project_slug': 'project-slug',
            'result': 'Failed',
            'label': 'Some sweet diff',
            'is_commit': True,
            'duration': 1234,
            'date_created': created,
            'date_started': started,
            'date_finished': finished,
        }
        post_fn.assert_called_once_with(URL, expected_data)
