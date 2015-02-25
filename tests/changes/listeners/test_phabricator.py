from __future__ import absolute_import

from flask import current_app

import mock

from changes.constants import Result
from changes.testutils import TestCase
from changes.listeners.phabricator_listener import build_finished_handler
from changes.utils.http import build_uri


class PhabricatorListenerTest(TestCase):
    def setUp(self):
        super(PhabricatorListenerTest, self).setUp()
        current_app.config['PHABRICATOR_POST_BUILD_RESULT'] = True

    @mock.patch('changes.listeners.phabricator_listener.post_diff_comment')
    @mock.patch('changes.listeners.phabricator_listener.get_options')
    def test_no_target(self, get_options, phab):
        project = self.create_project(name='test', slug='test')
        build = self.create_build(project, result=Result.failed)
        build_finished_handler(build_id=build.id.hex)
        self.assertEquals(phab.call_count, 0)

    @mock.patch('changes.listeners.phabricator_listener.post_diff_comment')
    @mock.patch('changes.listeners.phabricator_listener.get_options')
    def test_blacklisted_project(self, get_options, phab):
        project = self.create_project(name='test', slug='test')
        self.assertEquals(phab.call_count, 0)
        build = self.create_build(project, result=Result.failed, target='D1')
        build_finished_handler(build_id=build.id.hex)
        self.assertEquals(phab.call_count, 0)
        get_options.assert_called_once_with(project.id)

    @mock.patch('changes.listeners.phabricator_listener.post_diff_comment')
    @mock.patch('changes.listeners.phabricator_listener.get_options')
    def test_whitelisted_project(self, get_options, phab):
        get_options.return_value = {
            'phabricator.notify': '1'
        }
        project = self.create_project(name='test', slug='project-slug')
        self.assertEquals(phab.call_count, 0)
        build = self.create_build(project, result=Result.failed, target='D1')
        build_finished_handler(build_id=build.id.hex)

        get_options.assert_called_once_with(project.id)
        build_link = build_uri('/projects/{0}/builds/{1}/'.format(
            build.project.slug, build.id.hex))
        expected_msg = "red-x\nBuild Failed - test #1 (D1). Build Results: [link]({0})".format(
            build_link)

        phab.assert_called_once_with('1', expected_msg)
