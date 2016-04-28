from __future__ import absolute_import

from flask import current_app

import mock
import uuid

from changes.config import db
from changes.constants import Result, Status
from changes.models.repository import RepositoryBackend
from changes.testutils import TestCase as UnitTestCase
from changes.listeners.phabricator_listener import (
    build_finished_handler,
    post_commit_coverage,
    post_diff_coverage,
    )
from changes.utils.http import build_uri


class PhabricatorListenerTest(UnitTestCase):
    def setUp(self):
        super(PhabricatorListenerTest, self).setUp()
        current_app.config['PHABRICATOR_POST_BUILD_RESULT'] = True
        patcher = mock.patch('changes.utils.phabricator_utils.PhabricatorClient.connect')
        patcher.start().return_value = True
        self.addCleanup(patcher.stop)

    def create_project(self, notify='1', *args, **kwargs):
        project = super(PhabricatorListenerTest, self).create_project(*args, **kwargs)
        self.create_project_option(project, 'phabricator.notify', notify)
        return project

    @mock.patch('changes.utils.phabricator_utils.post_diff_comment')
    @mock.patch('changes.listeners.phabricator_listener.get_options')
    def test_no_target(self, get_options, post):
        project = self.create_project(name='test', slug='test')
        build = self.create_build(project, result=Result.failed, status=Status.finished)
        build_finished_handler(build_id=build.id.hex)
        self.assertEquals(post.call_count, 0)

    @mock.patch('changes.utils.phabricator_utils.post_diff_comment')
    @mock.patch('changes.listeners.phabricator_listener.get_options')
    def test_blacklisted_project(self, get_options, post):
        project = self.create_project(name='test', slug='test')
        self.assertEquals(post.call_count, 0)
        build = self.create_build(project, result=Result.failed, target='D1', status=Status.finished)
        build_finished_handler(build_id=build.id.hex)
        self.assertEquals(post.call_count, 0)
        get_options.assert_called_once_with(project.id)

    @mock.patch('changes.utils.phabricator_utils.post_diff_comment')
    @mock.patch('changes.listeners.phabricator_listener.get_options')
    def test_arc_test_build(self, get_options, post):
        get_options.return_value = {
            'phabricator.notify': '1'
        }
        project = self.create_project(name='test', slug='project-slug')
        self.assertEquals(post.call_count, 0)
        build = self.create_build(project, result=Result.failed, target='D1', status=Status.finished,
                tags=['arc test'])
        build_finished_handler(build_id=build.id.hex)
        self.assertEquals(post.call_count, 0)

    @mock.patch('changes.utils.phabricator_utils.post_diff_comment')
    @mock.patch('changes.listeners.phabricator_listener.get_options')
    def test_whitelisted_project(self, get_options, post):
        get_options.return_value = {
            'phabricator.notify': '1'
        }
        project = self.create_project(name='test', slug='project-slug')
        self.assertEquals(post.call_count, 0)
        build = self.create_build(project, result=Result.failed, target='D1', status=Status.finished)
        build_finished_handler(build_id=build.id.hex)

        get_options.assert_called_once_with(project.id)
        build_link = build_uri('/find_build/{0}/'.format(build.id.hex))
        expected_msg = "test build Failed {{icon times, color=red}} ([results]({0})).".format(
            build_link
        )

        post.assert_called_once_with('1', expected_msg, mock.ANY)

    @mock.patch('changes.utils.phabricator_utils.post_diff_comment')
    @mock.patch('changes.listeners.phabricator_listener.get_options')
    def test_build_failure_with_tests_and_no_base_build(self, get_options, post):
        get_options.return_value = {
            'phabricator.notify': '1'
        }
        project = self.create_project(name='Server', slug='project-slug')
        self.assertEquals(post.call_count, 0)

        patch = self.create_patch()
        source = self.create_source(project, revision_sha='1235', patch=patch)
        build = self.create_build(project, result=Result.failed, target='D1',
                                  source=source, status=Status.finished)
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
        build_link = build_uri('/find_build/{0}/'.format(build.id.hex))
        failure_link = build_uri('/build_tests/{0}/'.format(build.id.hex))

        test_link = build_uri('/build_test/{0}/{1}/'.format(
            build.id.hex,
            testcase.id.hex
        ))
        test_desc = "[test_foo](%s)" % test_link
        expected_msg = """Server build Failed {{icon times, color=red}} ([results]({0})). There were a total of 1 [test failures]({1}), but we could not determine if any of these tests were previously failing.

**All failures (1):**
|Test Name | Package|
|--|--|
|{2}|test.group.ClassName|"""

        post.assert_called_once_with('1', expected_msg.format(build_link, failure_link, test_desc), mock.ANY)

    @mock.patch('changes.utils.phabricator_utils.post_diff_comment')
    @mock.patch('changes.listeners.phabricator_listener.get_options')
    def test_build_failure_with_tests_and_no_base_job(self, get_options, post):
        get_options.return_value = {
            'phabricator.notify': '1'
        }
        project = self.create_project(name='Server', slug='project-slug')
        base_source = self.create_source(project, revision_sha='1235')
        base_build = self.create_build(project, result=Result.passed,
                                       source=base_source,
                                       status=Status.finished)
        self.assertEquals(post.call_count, 0)

        patch = self.create_patch()
        source = self.create_source(project, revision_sha='1235', patch=patch)
        build = self.create_build(project, result=Result.failed, target='D1',
                                  source=source, status=Status.finished)
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
        build_link = build_uri('/find_build/{0}/'.format(build.id.hex))
        failure_link = build_uri('/build_tests/{0}/'.format(build.id.hex))

        test_link = build_uri('/build_test/{0}/{1}/'.format(
            build.id.hex,
            testcase.id.hex,
        ))
        test_desc = "[test_foo](%s)" % test_link
        expected_msg = """Server build Failed {{icon times, color=red}} ([results]({0})). There were a total of 1 [test failures]({1}), but we could not determine if any of these tests were previously failing.

**All failures (1):**
|Test Name | Package|
|--|--|
|{2}|test.group.ClassName|"""

        post.assert_called_once_with('1', expected_msg.format(build_link, failure_link, test_desc), mock.ANY)

    @mock.patch('changes.utils.phabricator_utils.post_diff_comment')
    @mock.patch('changes.listeners.phabricator_listener.get_options')
    def test_build_failure_with_tests(self, get_options, post):
        get_options.return_value = {
            'phabricator.notify': '1'
        }
        project = self.create_project(name='Server', slug='project-slug')
        base_source = self.create_source(project, revision_sha='1235')
        base_build = self.create_build(project, result=Result.passed, source=base_source,
                                       status=Status.finished)
        self.create_job(build=base_build)
        self.assertEquals(post.call_count, 0)

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
        build_link = build_uri('/find_build/{0}/'.format(build.id.hex))
        failure_link = build_uri('/build_tests/{0}/'.format(build.id.hex))

        test_link = build_uri('/build_test/{0}/{1}/'.format(
            build.id.hex,
            testcase.id.hex,
        ))
        test_desc = "[test_foo](%s)" % test_link
        expected_msg = """Server build Failed {{icon times, color=red}} ([results]({0})). There were 1 new [test failures]({1})

**New failures (1):**
|Test Name | Package|
|--|--|
|{2}|test.group.ClassName|"""

        post.assert_called_once_with('1', expected_msg.format(build_link, failure_link, test_desc), mock.ANY)

    @mock.patch('changes.listeners.phabricator_listener.get_test_failures_in_base_commit')
    @mock.patch('changes.utils.phabricator_utils.post_diff_comment')
    @mock.patch('changes.listeners.phabricator_listener.get_options')
    def test_no_new_failures(self, get_options, post, get_base_failures):
        get_options.return_value = {
            'phabricator.notify': '1'
        }
        project = self.create_project(name='Server', slug='project-slug')
        self.assertEquals(post.call_count, 0)
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
        build_link = build_uri('/find_build/{0}/'.format(build.id.hex))
        failure_link = build_uri('/build_tests/{0}/'.format(build.id.hex))

        test_link = build_uri('/build_test/{0}/{1}/'.format(
            build.id.hex,
            testcase.id.hex,
        ))
        test_desc = "[test_foo](%s)" % test_link
        expected_msg = """Server build Failed {{icon times, color=red}} ([results]({0})). There were 0 new [test failures]({1})

**Failures in parent revision (1):**
|Test Name | Package|
|--|--|
|{2}|test.group.ClassName|"""

        post.assert_called_once_with('1', expected_msg.format(build_link, failure_link, test_desc), mock.ANY)

    @mock.patch('changes.listeners.phabricator_listener.get_test_failures_in_base_commit')
    @mock.patch('changes.utils.phabricator_utils.post_diff_comment')
    @mock.patch('changes.listeners.phabricator_listener.get_options')
    def test_parent_and_new_failures(self, get_options, post, get_base_failures):
        def get_test_desc(build, testcase, test_name):
            test_link = build_uri('/build_test/{0}/{1}/'.format(
                build.id.hex,
                testcase.id.hex,
            ))
            return "[%s](%s)" % (test_name, test_link)
        get_options.return_value = {
            'phabricator.notify': '1'
        }
        project = self.create_project(name='Server', slug='project-slug')
        self.assertEquals(post.call_count, 0)
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
        build_link = build_uri('/find_build/{0}/'.format(build.id.hex))
        failure_link = build_uri('/build_tests/{0}/'.format(build.id.hex))

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

        post.assert_called_once_with('1', expected_msg.format(build_link, failure_link, test_desc2, test_desc), mock.ANY)

    @mock.patch('changes.utils.phabricator_utils.post_diff_comment')
    @mock.patch('changes.listeners.phabricator_listener.get_options')
    def test_max_shown_build_failures(self, get_options, post):
        get_options.return_value = {
            'phabricator.notify': '1'
        }
        project = self.create_project(name='Server', slug='project-slug')
        self.assertEquals(post.call_count, 0)
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
        build_link = build_uri('/find_build/{0}/'.format(build.id.hex))
        failure_link = build_uri('/build_tests/{0}/'.format(build.id.hex))

        assert post.call_count == 1
        (diff_id, comment, phab), _ = post.call_args
        assert diff_id == '1'
        shown_test_count = 0
        for testcase in testcases:
            test_link = build_uri('/build_test/{0}/{1}/'.format(
                build.id.hex,
                testcase.id.hex,
            ))
            if test_link in comment:
                shown_test_count += 1
        assert shown_test_count == max_shown
        assert 'Server build Failed {{icon times, color=red}} ([results]({0})). There were {2} new [test failures]({1})'.format(build_link, failure_link, total_test_count)
        assert '|...more...|...|' in comment

    @mock.patch('changes.utils.phabricator_utils.post_diff_comment')
    @mock.patch('changes.listeners.phabricator_listener.get_options')
    def test_multiple_builds(self, get_options, post):
        get_options.return_value = {
            'phabricator.notify': '1'
        }
        project1 = self.create_project(name='Server', slug='project-slug')
        project2 = self.create_project(name='Server2', slug='project-slug2')
        self.assertEquals(post.call_count, 0)
        collection_id = uuid.uuid4()

        def create_build(result, project):
            base_source = self.create_source(project, revision_sha='1235')
            base_build = self.create_build(project, result=Result.passed,
                                           source=base_source,
                                           status=Status.finished)
            self.create_job(build=base_build)

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

        build_link = build_uri('/find_build/{0}/'.format(build1.id.hex))
        build2_link = build_uri('/find_build/{0}/'.format(build2.id.hex))
        failure_link = build_uri('/build_tests/{0}/'.format(build1.id.hex))

        test_link = build_uri('/build_test/{0}/{1}/'.format(
            build1.id.hex,
            testcase1.id.hex,
        ))
        test_desc = "[test_foo](%s)" % test_link
        expected_msg = """Server build Failed {{icon times, color=red}} ([results]({0})). There were 1 new [test failures]({1})

**New failures (1):**
|Test Name | Package|
|--|--|
|{2}|test.group.ClassName|

Server2 build Passed {{icon check, color=green}} ([results]({3}))."""

        post.assert_called_once_with('1', expected_msg.format(build_link, failure_link, test_desc, build2_link), mock.ANY)

    @mock.patch('changes.utils.phabricator_utils.post_diff_comment')
    def test_remaining_build(self, post):
        project1 = self.create_project(name='project1', slug='project1')
        project2 = self.create_project(name='project2', slug='project2')
        collection_id = uuid.uuid4()
        build1 = self.create_build(project1, target='D1', collection_id=collection_id, result=Result.failed, status=Status.finished)
        build2 = self.create_build(project2, target='D1', collection_id=collection_id, result=Result.unknown, status=Status.in_progress)

        build_finished_handler(build_id=build1.id.hex)
        assert post.call_count == 0

        build2.result = Result.failed
        build2.status = Status.finished
        db.session.add(build2)
        db.session.commit()

        build_finished_handler(build_id=build2.id.hex)
        assert post.call_count == 1

        args, kwargs = post.call_args
        id, msg, request = args
        assert 'project1' in msg
        assert 'project2' in msg

    @mock.patch('changes.utils.phabricator_utils.post_diff_comment')
    def test_remaining_nonnotifying_build(self, post):
        project1 = self.create_project(name='project1', slug='project1')
        project2 = self.create_project(name='project2', slug='project2', notify='0')
        collection_id = uuid.uuid4()
        build1 = self.create_build(project1, target='D1', collection_id=collection_id, result=Result.failed, status=Status.finished)
        build2 = self.create_build(project2, target='D1', collection_id=collection_id, result=Result.unknown, status=Status.in_progress)

        build_finished_handler(build_id=build1.id.hex)
        assert post.call_count == 1

        args, kwargs = post.call_args
        id, msg, request = args
        assert 'project1' in msg
        assert 'project2' not in msg

        build2.result = Result.failed
        build2.status = Status.finished
        db.session.add(build2)
        db.session.commit()

        # should not change anything
        build_finished_handler(build_id=build2.id.hex)
        assert post.call_count == 1

    @mock.patch('changes.utils.phabricator_utils.post_diff_comment')
    def test_nonnotifying_build(self, post):
        project1 = self.create_project(name='project1', slug='project1', notify='0')
        project2 = self.create_project(name='project2', slug='project2')
        collection_id = uuid.uuid4()
        build1 = self.create_build(project1, target='D1', collection_id=collection_id, result=Result.failed, status=Status.finished)
        build2 = self.create_build(project2, target='D1', collection_id=collection_id, result=Result.unknown, status=Status.in_progress)

        build_finished_handler(build_id=build1.id.hex)
        assert post.call_count == 0

        build2.result = Result.failed
        build2.status = Status.finished
        db.session.add(build2)
        db.session.commit()

        build_finished_handler(build_id=build2.id.hex)
        assert post.call_count == 1

        args, kwargs = post.call_args
        id, msg, request = args
        assert 'project1' not in msg
        assert 'project2' in msg

    @mock.patch('changes.utils.phabricator_utils.post_diff_comment')
    @mock.patch('changes.listeners.phabricator_listener.get_options')
    def test_slug_escape(self, get_options, post):
        get_options.return_value = {
            'phabricator.notify': '1'
        }
        project = self.create_project(name='Server', slug='project-(slug)')
        self.assertEquals(post.call_count, 0)
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
        build_link = build_uri('/find_build/{0}/'.format(build.id.hex))

        expected_msg = 'Server build Passed {{icon check, color=green}} ([results]({0})).'
        post.assert_called_once_with('1', expected_msg.format(build_link), mock.ANY)

    @mock.patch('changes.utils.phabricator_utils.post_diff_comment')
    @mock.patch('changes.listeners.phabricator_listener.post_diff_coverage')
    @mock.patch('changes.listeners.phabricator_listener.merged_coverage_data')
    @mock.patch('changes.listeners.phabricator_listener.get_options')
    def test_coverage_posted(self, get_options, merged_coverage_data,
                             post_diff_coverage, post_diff_comment):
        get_options.return_value = {
            'phabricator.notify': '1',
            'phabricator.coverage': '1',
        }
        project = self.create_project(name='Server', slug='project-slug')
        patch = self.create_patch()
        source = self.create_source(project, revision_sha='1235', patch=patch)
        build = self.create_build(project, result=Result.failed, target='D1', source=source, status=Status.finished)
        job = self.create_job(build=build)

        cov = {"file": "NUC"}
        merged_coverage_data.return_value = cov

        build_finished_handler(build_id=build.id.hex)

        assert post_diff_comment.call_count == 1
        assert post_diff_coverage.call_count == 1
        post_diff_coverage.assert_called_once_with('1', cov, mock.ANY)

    @mock.patch('changes.utils.phabricator_utils.post_diff_comment')
    @mock.patch('changes.listeners.phabricator_listener.post_diff_coverage')
    @mock.patch('changes.listeners.phabricator_listener.merged_coverage_data')
    @mock.patch('changes.listeners.phabricator_listener.get_options')
    def test_no_coverage_posted(self, get_options, merged_coverage_data,
                             post_diff_coverage, post_diff_comment):
        get_options.return_value = {
            'phabricator.notify': '1',
            'phabricator.coverage': '0',  # With this off, no coverage should be posted
        }
        project = self.create_project(name='Server', slug='project-slug')
        patch = self.create_patch()
        source = self.create_source(project, revision_sha='1235', patch=patch)
        build = self.create_build(project, result=Result.passed, target='D1', source=source, status=Status.finished)
        job = self.create_job(build=build)

        cov = {"file": "NUC"}
        merged_coverage_data.return_value = cov

        build_finished_handler(build_id=build.id.hex)

        assert post_diff_comment.call_count == 1
        assert post_diff_coverage.call_count == 0

    def test_post_diff_coverage(self):
        phab = mock.MagicMock()
        post_diff_coverage('1', {"file": "NUC"}, phab)
        assert phab.post.call_count == 3
        call0, call1, call2 = phab.post.call_args_list
        # Each call is a pair (positional_args, keyword_args)
        assert call0[0] == ('differential.query',)
        assert call1[0] == ('harbormaster.queryautotargets',)
        assert call2[0] == ('harbormaster.sendmessage',)
        # We'll trust the code for the keyword args

    @mock.patch('changes.utils.phabricator_utils.post_diff_comment')
    @mock.patch('changes.listeners.phabricator_listener.post_commit_coverage')
    @mock.patch('changes.listeners.phabricator_listener.post_diff_coverage')
    @mock.patch('changes.listeners.phabricator_listener.merged_coverage_data')
    @mock.patch('changes.listeners.phabricator_listener.get_options')
    def test_commit_coverage_posted(self, get_options, merged_coverage_data,
                                    post_diff_coverage, post_commit_coverage,
                                    post_diff_comment):
        get_options.return_value = {
            'phabricator.notify': '1',
            'phabricator.coverage': '1',
        }
        repo = self.create_repo(backend=RepositoryBackend.git)
        self.create_option(name='phabricator.callsign', value='BOO', item_id=repo.id)
        project = self.create_project(name='Server', repository=repo)
        source = self.create_source(project)
        revision_id = 12345
        build = self.create_build(project,
                                  result=Result.passed,
                                  source=source,
                                  status=Status.finished,
                                  tags=['commit'],
                                  message='commit message\nDifferential Revision: '
                                  'https://phabricator.example.com/D{}'.format(revision_id))
        job = self.create_job(build=build)

        cov = {"file": "NUC"}
        merged_coverage_data.return_value = cov

        build_finished_handler(build_id=build.id.hex)

        assert post_diff_comment.call_count == 0
        assert post_diff_coverage.call_count == 1
        post_diff_coverage.assert_called_once_with(revision_id, cov, mock.ANY)
        assert post_commit_coverage.call_count == 1
        post_commit_coverage.assert_called_once_with('BOO', 'master', source.revision_sha, cov, mock.ANY)

    def test_post_commit_coverage(self):
        phab = mock.MagicMock()
        post_commit_coverage('BOO', 'master', '12345', {"file": "NUC"}, phab)
        assert phab.post.call_count == 2
        call0, call1 = phab.post.call_args_list
        # Each call is a pair (positional_args, keyword_args)
        assert call0[0] == ('repository.query',)
        assert call1[0] == ('diffusion.updatecoverage',)
        # We'll trust the code for the keyword args
