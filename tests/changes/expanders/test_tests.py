from __future__ import absolute_import

import pytest

from mock import patch

from changes.constants import Status, Result
from changes.expanders.tests import TestsExpander
from changes.testutils import TestCase


@pytest.mark.parametrize('test_name, normalized', [
    ('foo/bar.py', ('foo', 'bar')),
    ('foo.bar.test_baz', ('foo', 'bar', 'test_baz')),
])
def test_normalize_test_segments(test_name, normalized):
    assert TestsExpander._normalize_test_segments(test_name) == normalized


class TestsExpanderTest(TestCase):
    def setUp(self):
        super(TestsExpanderTest, self).setUp()
        self.project = self.create_project()

    def get_expander(self, data):
        return TestsExpander(self.project, data)

    def test_validate(self):
        with pytest.raises(AssertionError):
            self.get_expander({}).validate()

        with pytest.raises(AssertionError):
            self.get_expander({'tests': []}).validate()

        with pytest.raises(AssertionError):
            self.get_expander({'cmd': 'echo 1', 'tests': []}).validate()

        self.get_expander({
            'tests': [],
            'cmd': 'echo {test_names}',
        }).validate()

    def test_get_test_stats(self):
        build = self.create_build(
            project=self.project,
            status=Status.finished,
            result=Result.passed,
        )
        job = self.create_job(build)
        self.create_test(job, name='foo.bar.test_baz', duration=50)
        self.create_test(job, name='foo.bar.test_bar', duration=25)

        expander = self.get_expander({})
        results, avg_time = expander.get_test_stats(self.project.slug)

        assert avg_time == 37

        assert results[('foo', 'bar')] == 75
        assert results[('foo', 'bar', 'test_baz')] == 50
        assert results[('foo', 'bar', 'test_bar')] == 25

    @patch.object(TestsExpander, 'get_test_stats')
    def test_expand(self, mock_get_test_stats):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        mock_get_test_stats.return_value = {
            ('foo', 'bar'): 50,
            ('foo', 'baz'): 15,
            ('foo', 'bar', 'test_biz'): 10,
            ('foo', 'bar', 'test_buz'): 200,
        }, 68

        results = list(self.get_expander({
            'cmd': 'py.test --junit=junit.xml {test_names}',
            'tests': [
                'foo/bar.py',
                'foo/baz.py',
                'foo.bar.test_biz',
                'foo.bar.test_buz',
            ],
        }).expand(job=job, max_executors=2))

        results.sort(key=lambda x: x.data['weight'], reverse=True)

        assert len(results) == 2
        assert results[0].label == 'py.test --junit=junit.xml foo.bar.test_buz'
        assert results[0].data['weight'] == 201
        assert set(results[0].data['tests']) == set(['foo.bar.test_buz'])
        assert results[0].data['shard_count'] == 2
        assert results[0].data['artifact_search_path'] is None
        assert results[0].commands[0].label == results[0].label
        assert results[0].commands[0].script == results[0].label

        assert results[1].label == 'py.test --junit=junit.xml foo/bar.py foo/baz.py foo.bar.test_biz'
        assert results[1].data['weight'] == 78
        assert set(results[1].data['tests']) == set(['foo/bar.py', 'foo/baz.py', 'foo.bar.test_biz'])
        assert results[1].data['shard_count'] == 2
        assert results[1].data['artifact_search_path'] is None
        assert results[1].commands[0].label == results[1].label
        assert results[1].commands[0].script == results[1].label

    @patch.object(TestsExpander, 'get_test_stats')
    def test_expand_with_artifact_search_path(self, mock_get_test_stats):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        mock_get_test_stats.return_value = {
            ('foo', 'bar'): 50,
            ('foo', 'baz'): 15,
            ('foo', 'bar', 'test_biz'): 10,
            ('foo', 'bar', 'test_buz'): 200,
        }, 68

        results = list(self.get_expander({
            'cmd': 'py.test --junit=junit.xml {test_names}',
            'tests': [
                'foo/bar.py',
                'foo/baz.py',
                'foo.bar.test_biz',
                'foo.bar.test_buz',
            ],
            'artifact_search_path': '/tmp/artifacts',
        }).expand(job=job, max_executors=2))

        results.sort(key=lambda x: x.data['weight'], reverse=True)

        assert len(results) == 2
        assert results[0].label == 'py.test --junit=junit.xml foo.bar.test_buz'
        assert results[0].data['weight'] == 201
        assert set(results[0].data['tests']) == set(['foo.bar.test_buz'])
        assert results[0].data['shard_count'] == 2
        assert results[0].data['artifact_search_path'] == '/tmp/artifacts'
        assert results[0].commands[0].label == results[0].label
        assert results[0].commands[0].script == results[0].label

        assert results[1].label == 'py.test --junit=junit.xml foo/bar.py foo/baz.py foo.bar.test_biz'
        assert results[1].data['weight'] == 78
        assert set(results[1].data['tests']) == set(['foo/bar.py', 'foo/baz.py', 'foo.bar.test_biz'])
        assert results[1].data['shard_count'] == 2
        assert results[1].data['artifact_search_path'] == '/tmp/artifacts'
        assert results[1].commands[0].label == results[1].label
        assert results[1].commands[0].script == results[1].label

    @patch.object(TestsExpander, 'get_test_stats')
    def test_expand_with_artifact_search_path_empty(self, mock_get_test_stats):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        mock_get_test_stats.return_value = {
            ('foo', 'bar'): 50,
            ('foo', 'baz'): 15,
            ('foo', 'bar', 'test_biz'): 10,
            ('foo', 'bar', 'test_buz'): 200,
        }, 68

        results = list(self.get_expander({
            'cmd': 'py.test --junit=junit.xml {test_names}',
            'tests': [
                'foo/bar.py',
                'foo/baz.py',
                'foo.bar.test_biz',
                'foo.bar.test_buz',
            ],
            'artifact_search_path': '',
        }).expand(job=job, max_executors=2))

        results.sort(key=lambda x: x.data['weight'], reverse=True)

        assert len(results) == 2
        assert results[0].label == 'py.test --junit=junit.xml foo.bar.test_buz'
        assert results[0].data['weight'] == 201
        assert set(results[0].data['tests']) == set(['foo.bar.test_buz'])
        assert results[0].data['shard_count'] == 2
        assert results[0].data['artifact_search_path'] is None
        assert results[0].commands[0].label == results[0].label
        assert results[0].commands[0].script == results[0].label

        assert results[1].label == 'py.test --junit=junit.xml foo/bar.py foo/baz.py foo.bar.test_biz'
        assert results[1].data['weight'] == 78
        assert set(results[1].data['tests']) == set(['foo/bar.py', 'foo/baz.py', 'foo.bar.test_biz'])
        assert results[1].data['shard_count'] == 2
        assert results[1].data['artifact_search_path'] is None
        assert results[1].commands[0].label == results[1].label
        assert results[1].commands[0].script == results[1].label
