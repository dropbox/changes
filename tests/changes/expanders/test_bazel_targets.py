from __future__ import absolute_import

import pytest

from mock import patch

from changes.config import db
from changes.constants import Status, Result, ResultSource, SelectiveTestingPolicy
from changes.expanders.bazel_targets import BazelTargetsExpander
from changes.models.bazeltarget import BazelTarget
from changes.testutils import TestCase


class BazelTargetsExpanderTest(TestCase):

    def setUp(self):
        super(BazelTargetsExpanderTest, self).setUp()
        self.project = self.create_project()

    def get_expander(self, data):
        return BazelTargetsExpander(self.project, data)

    def test_validate(self):
        with pytest.raises(AssertionError):
            self.get_expander({}).validate()

        with pytest.raises(AssertionError):
            self.get_expander({'affected_targets': []}).validate()

        with pytest.raises(AssertionError):
            self.get_expander({'cmd': 'echo 1', 'affected_targets': []}).validate()

        with pytest.raises(AssertionError):
            self.get_expander(
                {'cmd': 'echo {target_names}', 'affected_targets': []}).validate()

        with pytest.raises(AssertionError):
            self.get_expander({
                'affected_targets': [],
                'cmd': 'echo {target_names}',
                'artifact_search_path': 'path'
            }).validate()

        self.get_expander({
            'affected_targets': [],
            'unaffected_targets': [],
            'cmd': 'echo {target_names}',
            'artifact_search_path': 'path'
        }).validate()

    def test_get_target_stats(self):
        build = self.create_build(
            project=self.project,
            status=Status.finished,
            result=Result.passed,
        )
        job = self.create_job(build)
        phase = self.create_jobphase(job)
        jobstep = self.create_jobstep(phase)
        self.create_target(job, jobstep, name='//foo/bar:baz', duration=50)
        self.create_target(job, jobstep, name='//foo:test', duration=25)
        no_duration = self.create_target(
            job, jobstep, name='//foo/bar/baz:test')
        no_duration.duration = None
        db.session.add(no_duration)
        db.session.commit()

        expander = self.get_expander({})
        results, avg_time = expander.get_target_stats(self.project.slug)

        assert avg_time == 37

        assert results['//foo/bar:baz'] == 50
        assert results['//foo:test'] == 25
        assert '//foo/bar/baz:test' not in results

    @patch.object(BazelTargetsExpander, 'get_target_stats')
    def test_expand(self, mock_get_target_stats):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        mock_get_target_stats.return_value = {
            '//foo/bar:test': 50,
            '//foo/baz:target': 15,
            '//foo/bar/test_biz:test': 10,
            '//foo/bar/test_buz:test': 200,
        }, 68

        results = list(self.get_expander({
            'cmd': 'bazel test {target_names}',
            'affected_targets': [
                '//foo/bar:test',
                '//foo/baz:target',
            ],
            'unaffected_targets': [
                '//foo/bar/test_biz:test',
                '//foo/bar/test_buz:test',
            ],
            'artifact_search_path': 'artifacts/'
        }).expand(job=job, max_executors=2))

        results.sort(key=lambda x: x.data['weight'], reverse=True)

        assert len(results) == 2
        assert results[0].label == 'bazel test //foo/bar/test_buz:test'
        assert results[0].data['weight'] == 201
        assert set(results[0].data['targets']) == set(
            ['//foo/bar/test_buz:test'])
        assert results[0].data['shard_count'] == 2
        assert results[0].data['artifact_search_path'] == 'artifacts/'
        assert results[0].commands[0].label == results[0].label
        assert results[0].commands[0].script == results[0].label

        assert results[
            1].label == 'bazel test //foo/bar:test //foo/baz:target //foo/bar/test_biz:test'
        assert results[1].data['weight'] == 78
        assert set(results[1].data['targets']) == set(
            ['//foo/bar:test', '//foo/baz:target', '//foo/bar/test_biz:test'])
        assert results[1].data['shard_count'] == 2
        assert results[1].data['artifact_search_path'] == 'artifacts/'
        assert results[1].commands[0].label == results[1].label
        assert results[1].commands[0].script == results[1].label

    @patch.object(BazelTargetsExpander, 'get_target_stats')
    def test_expand_with_selective_testing(self, mock_get_target_stats):
        project = self.create_project()
        build = self.create_build(project, selective_testing_policy=SelectiveTestingPolicy.enabled)
        job = self.create_job(build)
        mock_get_target_stats.return_value = {
            '//foo/bar:test': 50,
            '//foo/baz:target': 15,
            '//foo/bar/test_biz:test': 10,
            '//foo/bar/test_buz:test': 200,
        }, 68

        results = list(self.get_expander({
            'cmd': 'bazel test {target_names}',
            'affected_targets': [
                '//foo/bar:test',
                '//foo/baz:target',
            ],
            'unaffected_targets': [
                '//foo/bar/test_biz:test',
                '//foo/bar/test_buz:test',
            ],
            'artifact_search_path': 'artifacts/'
        }).expand(job=job, max_executors=2))

        results.sort(key=lambda x: x.data['weight'], reverse=True)

        assert len(results) == 2
        assert results[0].label == 'bazel test //foo/bar:test'
        assert results[0].data['weight'] == 51
        assert set(results[0].data['targets']) == set(
            ['//foo/bar:test'])
        assert results[0].data['shard_count'] == 2
        assert results[0].data['artifact_search_path'] == 'artifacts/'
        assert results[0].commands[0].label == results[0].label
        assert results[0].commands[0].script == results[0].label

        assert results[
            1].label == 'bazel test //foo/baz:target'
        assert results[1].data['weight'] == 16
        assert set(results[1].data['targets']) == set(
            ['//foo/baz:target'])
        assert results[1].data['shard_count'] == 2
        assert results[1].data['artifact_search_path'] == 'artifacts/'
        assert results[1].commands[0].label == results[1].label
        assert results[1].commands[0].script == results[1].label

        db.session.commit()
        for unaffected in ['//foo/bar/test_biz:test', '//foo/bar/test_buz:test']:
            assert BazelTarget.query.filter(
                BazelTarget.name == unaffected,
                BazelTarget.job == job,
                BazelTarget.result == Result.unknown,
                BazelTarget.status == Status.unknown,
                BazelTarget.result_source == ResultSource.from_parent,
            ).count() == 1

    @patch.object(BazelTargetsExpander, 'get_target_stats')
    def test_expand_with_selective_testing_None(self, mock_get_target_stats):
        # test that selective_testing_policy = None implies disabled
        project = self.create_project()
        build = self.create_build(project)
        build.selective_testing_policy = None
        db.session.add(build)
        db.session.commit()
        assert build.selective_testing_policy is None
        job = self.create_job(build)
        mock_get_target_stats.return_value = {
            '//foo/bar:test': 50,
            '//foo/baz:target': 15,
            '//foo/bar/test_biz:test': 10,
            '//foo/bar/test_buz:test': 200,
        }, 68

        results = list(self.get_expander({
            'cmd': 'bazel test {target_names}',
            'affected_targets': [
                '//foo/bar:test',
                '//foo/baz:target',
            ],
            'unaffected_targets': [
                '//foo/bar/test_biz:test',
                '//foo/bar/test_buz:test',
            ],
            'artifact_search_path': 'artifacts/'
        }).expand(job=job, max_executors=2))

        results.sort(key=lambda x: x.data['weight'], reverse=True)

        assert len(results) == 2
        assert set(results[0].data['targets']) == set(
            ['//foo/bar/test_buz:test'])

        assert set(results[1].data['targets']) == set(
            ['//foo/bar:test', '//foo/baz:target', '//foo/bar/test_biz:test'])

    @patch.object(BazelTargetsExpander, 'get_target_stats')
    def test_expand_no_duration(self, mock_get_target_stats):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        mock_get_target_stats.return_value = {
            '//foo/bar:test': 50,
            '//foo/baz:target': 15,
            '//foo/bar/test_biz:test': 10,
            '//foo/bar/test_buz:test': 200,
        }, 68

        results = list(self.get_expander({
            'cmd': 'bazel test {target_names}',
            'affected_targets': [
                '//foo/bar:test',
                '//foo/baz:target',

                # if a target has no duration, it's not added to the target
                # stats dictionary
                '//foo/bar/baz:test',
            ],
            'unaffected_targets': [
                '//foo/bar/test_biz:test',
                '//foo/bar/test_buz:test',
            ],
            'artifact_search_path': 'artifacts/'
        }).expand(job=job, max_executors=2))

        results.sort(key=lambda x: x.data['weight'], reverse=True)

        assert len(results) == 2
        assert results[0].label == 'bazel test //foo/bar/test_buz:test'
        assert results[0].data['weight'] == 201
        assert set(results[0].data['targets']) == set(
            ['//foo/bar/test_buz:test'])
        assert results[0].data['shard_count'] == 2
        assert results[0].data['artifact_search_path'] == 'artifacts/'
        assert results[0].commands[0].label == results[0].label
        assert results[0].commands[0].script == results[0].label

        assert results[1].label == 'bazel test //foo/bar/baz:test //foo/bar:test //foo/baz:target //foo/bar/test_biz:test'
        assert results[1].data['weight'] == 147
        assert set(results[1].data['targets']) == set(
            ['//foo/bar:test', '//foo/baz:target', '//foo/bar/test_biz:test', '//foo/bar/baz:test'])
        assert results[1].data['shard_count'] == 2
        assert results[1].data['artifact_search_path'] == 'artifacts/'
        assert results[1].commands[0].label == results[1].label
        assert results[1].commands[0].script == results[1].label
