from __future__ import absolute_import

from flask import current_app

import responses

from changes.constants import Result, Status
from changes.listeners.build_finished_notifier import build_finished_handler
from changes.testutils import TestCase as UnitTestCase


class BuildFinishedNotifierTest(UnitTestCase):
    def setUp(self):
        super(BuildFinishedNotifierTest, self).setUp()

    @responses.activate
    def test_no_urls(self):
        project = self.create_project(name='test', slug='test')
        build = self.create_build(project, result=Result.failed, status=Status.finished)
        build_finished_handler(build.id)

    @responses.activate
    def test_two_urls(self):
        current_app.config['BUILD_FINISHED_URLS'] = [
            ('http://example.com/a', None),
            ('http://example.com/b', None),
        ]
        responses.add(responses.POST, 'http://example.com/a', status=200)
        responses.add(responses.POST, 'http://example.com/b', status=200)

        project = self.create_project(name='test', slug='test')
        build = self.create_build(project, result=Result.failed, status=Status.finished)
        build_finished_handler(build.id)

        assert len(responses.calls) == 2

    @responses.activate
    def test_ignore_failure(self):
        current_app.config['BUILD_FINISHED_URLS'] = [
            ('http://example.com/a', None),
            ('http://example.com/b', None),
            ('http://example.com/c', None),
        ]
        responses.add(responses.POST, 'http://example.com/a', status=400)
        responses.add(responses.POST, 'http://example.com/b', status=500)
        responses.add(responses.POST, 'http://example.com/c', status=200)

        project = self.create_project(name='test', slug='test')
        build = self.create_build(project, result=Result.failed, status=Status.finished)
        build_finished_handler(build.id)

        assert len(responses.calls) == 3

    @responses.activate
    def test_various_statuses(self):
        current_app.config['BUILD_FINISHED_URLS'] = [
            ('http://example.com/a', None),
        ]
        responses.add(responses.POST, 'http://example.com/a', status=400)

        project = self.create_project(name='test', slug='test')

        build = self.create_build(project, result=Result.failed, status=Status.finished)
        build_finished_handler(build.id)

        build = self.create_build(project, result=Result.passed, status=Status.finished)
        build_finished_handler(build.id)

        build = self.create_build(project, result=Result.unknown, status=Status.finished)
        build_finished_handler(build.id)

        build = self.create_build(project, result=Result.infra_failed, status=Status.finished)
        build_finished_handler(build.id)

        assert len(responses.calls) == 4

    @responses.activate
    def test_string_compatability(self):
        current_app.config['BUILD_FINISHED_URLS'] = [
            'http://example.com/a',
            'http://example.com/b',
            'http://example.com/c',
        ]
        responses.add(responses.POST, 'http://example.com/a', status=400)
        responses.add(responses.POST, 'http://example.com/b', status=500)
        responses.add(responses.POST, 'http://example.com/c', status=200)

        project = self.create_project(name='test', slug='test')
        build = self.create_build(project, result=Result.failed, status=Status.finished)
        build_finished_handler(build.id)

        assert len(responses.calls) == 3
