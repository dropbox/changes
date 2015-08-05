from __future__ import absolute_import

from flask import current_app

import mock
import uuid

from changes.constants import Result, Status
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
        build = self.create_build(project, result=Result.failed, status=Status.finished)
        build_finished_handler(build_id=build.id.hex)
        self.assertEquals(phab.call_count, 0)

    @mock.patch('changes.listeners.phabricator_listener.post_diff_comment')
    @mock.patch('changes.listeners.phabricator_listener.get_options')
    def test_blacklisted_project(self, get_options, phab):
        project = self.create_project(name='test', slug='test')
        self.assertEquals(phab.call_count, 0)
        build = self.create_build(project, result=Result.failed, target='D1', status=Status.finished)
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
        build = self.create_build(project, result=Result.failed, target='D1', status=Status.finished)
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
        build = self.create_build(project, result=Result.failed, target='D1', source=source, status=Status.finished)
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
        build = self.create_build(project, result=Result.failed, target='D1', source=source, status=Status.finished)
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

    @mock.patch('changes.listeners.phabricator_listener.get_test_failures_in_base_commit')
    @mock.patch('changes.listeners.phabricator_listener.post_diff_comment')
    @mock.patch('changes.listeners.phabricator_listener.get_options')
    def test_parent_and_new_failures(self, get_options, phab, get_base_failures):
        def get_test_desc(build, testcase, test_name):
            test_link = build_uri('/projects/{0}/builds/{1}/jobs/{2}/tests/{3}/'.format(
                build.project.slug,
                build.id.hex,
                testcase.job_id.hex,
                testcase.id.hex
            ))
            return "[%s](%s)" % (test_name, test_link)
        get_options.return_value = {
            'phabricator.notify': '1'
        }
        project = self.create_project(name='Server', slug='project-slug')
        self.assertEquals(phab.call_count, 0)
        patch = self.create_patch()
        source = self.create_source(project, revision_sha='1235', patch=patch)
        build = self.create_build(project, result=Result.failed, target='D1', source=source, status=Status.finished)
        job = self.create_job(build=build)
        testcase = self.create_test(
            package='test.group.ClassName',
            name='test.group.ClassName.test_foo',
            job=job,
            duration=134,
            result=Result.failed,
            )
        testcase2 = self.create_test(
            package='test.group.ClassName',
            name='test.group.ClassName.test_foo2',
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

        test_desc = get_test_desc(build, testcase, 'test_foo')
        test_desc2 = get_test_desc(build, testcase2, 'test_foo2')
        expected_msg = """Server build Failed {{icon times, color=red}} ([results]({0})). There were 1 new [test failures]({1})

**New failures (1):**
|Test Name | Package|
|--|--|
|{2}|test.group.ClassName|

**Failures in parent revision (1):**
|Test Name | Package|
|--|--|
|{3}|test.group.ClassName|"""

        phab.assert_called_once_with('1', expected_msg.format(build_link, failure_link, test_desc2, test_desc))

    @mock.patch('changes.listeners.phabricator_listener.post_diff_comment')
    @mock.patch('changes.listeners.phabricator_listener.get_options')
    def test_max_shown_build_failures(self, get_options, phab):
        get_options.return_value = {
            'phabricator.notify': '1'
        }
        project = self.create_project(name='Server', slug='project-slug')
        self.assertEquals(phab.call_count, 0)
        patch = self.create_patch()
        source = self.create_source(project, revision_sha='1235', patch=patch)
        build = self.create_build(project, result=Result.failed, target='D1', source=source, status=Status.finished)
        job = self.create_job(build=build)
        max_shown = current_app.config.get('MAX_SHOWN_ITEMS_PER_BUILD_PHABRICATOR', 10)
        total_test_count = max_shown + 1
        testcases = []
        for i in range(total_test_count):
            testcases.append(self.create_test(
                package='test.group.ClassName',
                name='test.group.ClassName.test_foo{}'.format(i),
                job=job,
                duration=134,
                result=Result.failed,
                ))

        build_finished_handler(build_id=build.id.hex)

        get_options.assert_called_once_with(project.id)
        build_link = build_uri('/projects/{0}/builds/{1}/'.format(
            build.project.slug, build.id.hex))
        failure_link = build_uri('/projects/{0}/builds/{1}/tests/?result=failed'.format(
            build.project.slug, build.id.hex))

        assert phab.call_count == 1
        (diff_id, comment), _ = phab.call_args
        assert diff_id == '1'
        shown_test_count = 0
        for testcase in testcases:
            test_link = build_uri('/projects/{0}/builds/{1}/jobs/{2}/tests/{3}/'.format(
                build.project.slug,
                build.id.hex,
                testcase.job_id.hex,
                testcase.id.hex
            ))
            if test_link in comment:
                shown_test_count += 1
        assert shown_test_count == max_shown
        assert 'Server build Failed {{icon times, color=red}} ([results]({0})). There were {2} new [test failures]({1})'.format(build_link, failure_link, total_test_count)
        assert '|...more...|...|' in comment

    @mock.patch('changes.listeners.phabricator_listener.post_diff_comment')
    @mock.patch('changes.listeners.phabricator_listener.get_options')
    def test_multiple_builds(self, get_options, phab):
        get_options.return_value = {
            'phabricator.notify': '1'
        }
        project1 = self.create_project(name='Server', slug='project-slug')
        project2 = self.create_project(name='Server2', slug='project-slug2')
        self.assertEquals(phab.call_count, 0)
        collection_id = uuid.uuid4()

        def create_build(result, project):
            patch = self.create_patch()
            source = self.create_source(project, revision_sha='1235', patch=patch)
            build = self.create_build(project, result=result, target='D1', source=source, status=Status.finished, collection_id=collection_id)
            job = self.create_job(build=build)
            testcase = self.create_test(
                package='test.group.ClassName',
                name='test.group.ClassName.test_foo',
                job=job,
                duration=134,
                result=result,
                )
            return build, testcase

        build1, testcase1 = create_build(Result.failed, project1)
        build2, testcase2 = create_build(Result.passed, project2)

        build_finished_handler(build_id=build1.id.hex)

        build_link = build_uri('/projects/{0}/builds/{1}/'.format(
            build1.project.slug, build1.id.hex))
        build2_link = build_uri('/projects/{0}/builds/{1}/'.format(
            build2.project.slug, build2.id.hex))
        failure_link = build_uri('/projects/{0}/builds/{1}/tests/?result=failed'.format(
            build1.project.slug, build1.id.hex))

        test_link = build_uri('/projects/{0}/builds/{1}/jobs/{2}/tests/{3}/'.format(
            build1.project.slug,
            build1.id.hex,
            testcase1.job_id.hex,
            testcase1.id.hex
        ))
        test_desc = "[test_foo](%s)" % test_link
        expected_msg = """Server build Failed {{icon times, color=red}} ([results]({0})). There were 1 new [test failures]({1})

**New failures (1):**
|Test Name | Package|
|--|--|
|{2}|test.group.ClassName|

Server2 build Passed {{icon check, color=green}} ([results]({3}))."""

        phab.assert_called_once_with('1', expected_msg.format(build_link, failure_link, test_desc, build2_link))

    @mock.patch('changes.listeners.phabricator_listener.post_diff_comment')
    @mock.patch('changes.listeners.phabricator_listener.get_options')
    def test_slug_escape(self, get_options, phab):
        get_options.return_value = {
            'phabricator.notify': '1'
        }
        project = self.create_project(name='Server', slug='project-(slug)')
        self.assertEquals(phab.call_count, 0)
        patch = self.create_patch()
        source = self.create_source(project, revision_sha='1235', patch=patch)
        build = self.create_build(project, result=Result.passed, target='D1', source=source, status=Status.finished)
        job = self.create_job(build=build)
        testcase = self.create_test(
            package='test.group.ClassName',
            name='test.group.ClassName.test_foo',
            job=job,
            duration=134,
            result=Result.passed,
        )

        build_finished_handler(build_id=build.id.hex)

        get_options.assert_called_once_with(project.id)
        safe_slug = 'project-%28slug%29'
        build_link = build_uri('/projects/{0}/builds/{1}/'.format(
            safe_slug, build.id.hex))

        expected_msg = 'Server build Passed {{icon check, color=green}} ([results]({0})).'
        phab.assert_called_once_with('1', expected_msg.format(build_link))
