from __future__ import absolute_import

from flask import current_app

import mock

from changes.constants import Result
from changes.testutils import TestCase as UnitTestCase
from changes.listeners.phabricator_listener import build_finished_handler
from changes.utils.http import build_uri


class PhabricatorListenerTest(UnitTestCase):
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
        expected_msg = "test build Failed {{icon times, color=red}} ([results]({0})).".format(
            build_link
        )

        phab.assert_called_once_with('1', expected_msg)

    @mock.patch('changes.listeners.phabricator_listener.post_diff_comment')
    @mock.patch('changes.listeners.phabricator_listener.get_options')
    def test_build_failure_with_tests(self, get_options, phab):
        get_options.return_value = {
            'phabricator.notify': '1'
        }
        project = self.create_project(name='Server', slug='project-slug')
        self.assertEquals(phab.call_count, 0)
        patch = self.create_patch()
        source = self.create_source(project, revision_sha='1235', patch=patch)
        build = self.create_build(project, result=Result.failed, target='D1', source=source)
        job = self.create_job(build=build)
        testcase = self.create_test(
            package='test.group.ClassName',
            name='test.group.ClassName.test_foo',
            job=job,
            duration=134,
            result=Result.failed,
            )

        build_finished_handler(build_id=build.id.hex)

        get_options.assert_called_once_with(project.id)
        build_link = build_uri('/projects/{0}/builds/{1}/'.format(
            build.project.slug, build.id.hex))
        failure_link = build_uri('/projects/{0}/builds/{1}/tests/?result=failed'.format(
            build.project.slug, build.id.hex))

        test_link = build_uri('/projects/{0}/builds/{1}/jobs/{2}/tests/{3}/'.format(
            build.project.slug,
            build.id.hex,
            testcase.job_id.hex,
            testcase.id.hex
        ))
        test_desc = "[test_foo](%s)" % test_link
        expected_msg = """Server build Failed {{icon times, color=red}} ([results]({0})). There were 1 new [test failures]({1})

**New failures (1):**
|Test Name | Package|
|--|--|
|{2}|test.group.ClassName|"""

        phab.assert_called_once_with('1', expected_msg.format(build_link, failure_link, test_desc))

    @mock.patch('changes.listeners.phabricator_listener.get_test_failures_in_base_commit')
    @mock.patch('changes.listeners.phabricator_listener.post_diff_comment')
    @mock.patch('changes.listeners.phabricator_listener.get_options')
    def test_no_new_failures(self, get_options, phab, get_base_failures):
        get_options.return_value = {
            'phabricator.notify': '1'
        }
        project = self.create_project(name='Server', slug='project-slug')
        self.assertEquals(phab.call_count, 0)
        patch = self.create_patch()
        source = self.create_source(project, revision_sha='1235', patch=patch)
        build = self.create_build(project, result=Result.failed, target='D1', source=source)
        job = self.create_job(build=build)
        testcase = self.create_test(
            package='test.group.ClassName',
            name='test.group.ClassName.test_foo',
            job=job,
            duration=134,
            result=Result.failed,
            )
        get_base_failures.return_value = {testcase.name}

        build_finished_handler(build_id=build.id.hex)

        get_options.assert_called_once_with(project.id)
        build_link = build_uri('/projects/{0}/builds/{1}/'.format(
            build.project.slug, build.id.hex))
        failure_link = build_uri('/projects/{0}/builds/{1}/tests/?result=failed'.format(
            build.project.slug, build.id.hex))

        test_link = build_uri('/projects/{0}/builds/{1}/jobs/{2}/tests/{3}/'.format(
            build.project.slug,
            build.id.hex,
            testcase.job_id.hex,
            testcase.id.hex
        ))
        test_desc = "[test_foo](%s)" % test_link
        expected_msg = """Server build Failed {{icon times, color=red}} ([results]({0})). There were 0 new [test failures]({1})

**Failures in parent revision (1):**
|Test Name | Package|
|--|--|
|{2}|test.group.ClassName|"""

        phab.assert_called_once_with('1', expected_msg.format(build_link, failure_link, test_desc))
