from __future__ import absolute_import

import heapq
import logging

from hashlib import md5

from changes.api.client import api_client
from changes.backends.jenkins.buildsteps.collector import JenkinsCollectorBuilder, JenkinsCollectorBuildStep
from changes.config import db
from changes.constants import Result, Status
from changes.db.utils import get_or_create
from changes.jobs.sync_job_step import sync_job_step
from changes.models import Job, JobPhase, JobStep, TestCase
from changes.utils.agg import aggregate_result
from changes.utils.trees import build_flat_tree


class JenkinsTestCollectorBuilder(JenkinsCollectorBuilder):
    def get_default_job_phase_label(self, job, job_data):
        return 'Collect Tests'

    def get_required_artifact_suffix(self):
        """The initial (collect) step must return at least one artifact with
        this suffix, or it will be marked as failed.

        Returns:
            str: the required suffix
        """
        return 'tests.json'


class JenkinsTestCollectorBuildStep(JenkinsCollectorBuildStep):
    """
    Fires off a generic job with parameters:

        CHANGES_BID = UUID
        CHANGES_PID = project slug
        REPO_URL    = repository URL
        REPO_VCS    = hg/git
        REVISION    = sha/id of revision
        PATCH_URL   = patch to apply, if available
        SCRIPT      = command to run

    A "tests.json" is expected to be collected as an artifact with the following
    values:

        {
            "phase": "optional phase name",
            "cmd": "py.test --junit=junit.xml {test_names}",
            "path": "",
            "tests": [
                "foo.bar.test_baz",
                "foo.bar.test_bar"
            ]
        }

    The collected tests will be sorted and partitioned evenly across a set number
    of shards with the <cmd> value being passed a space-delimited list of tests.
    """
    builder_cls = JenkinsTestCollectorBuilder

    # TODO(dcramer): longer term we'd rather have this create a new phase which
    # actually executes a different BuildStep (e.g. of order + 1), but at the
    # time of writing the system only supports a single build step.
    def __init__(self, shards=None, max_shards=10, **kwargs):
        # TODO(josiah): migrate existing step configs to use "shards" and remove max_shards
        if shards:
            self.num_shards = shards
        else:
            self.num_shards = max_shards
        super(JenkinsTestCollectorBuildStep, self).__init__(**kwargs)

    def get_label(self):
        return 'Collect tests from job "{0}" on Jenkins'.format(self.job_name)

    def fetch_artifact(self, artifact, **kwargs):
        if artifact.data['fileName'].endswith('tests.json'):
            self._expand_jobs(artifact.step, artifact)
        else:
            builder = self.get_builder()
            builder.sync_artifact(artifact, **kwargs)

    def _validate_shards(self, phase_steps):
        """This returns passed/unknown based on whether the correct number of
        shards were run."""
        step_expanded_flags = [step.data.get('expanded', False) for step in phase_steps]
        assert all(step_expanded_flags) or not any(step_expanded_flags), \
            "Mixed expanded and non-expanded steps in phase!"
        expanded = step_expanded_flags[0]
        if not expanded:
            # This was the initial phase, not the expanded phase. No need to
            # check shards.
            return Result.passed

        if len(phase_steps) != self.num_shards:
            # TODO(josiah): we'd like to be able to record a FailureReason
            # here, but currently a FailureReason must correspond to a JobStep.
            logging.error("Build failed due to incorrect number of shards: expected %d, got %d",
                          self.num_shards, len(phase_steps))
            return Result.unknown
        return Result.passed

    def validate_phase(self, phase):
        """Called when a job phase is ready to be finished.

        This is responsible for setting the phases's final result. We verify
        that the proper number of steps were created in the second (i.e.
        expanded) phase."""
        phase.result = aggregate_result([s.result for s in phase.steps] +
                                        [self._validate_shards(phase.steps)])

    def get_test_stats(self, project):
        response = api_client.get('/projects/{project}/'.format(
            project=project.slug))
        last_build = response['lastPassingBuild']

        if not last_build:
            return {}, 0

        # XXX(dcramer): ideally this would be abstractied via an API
        job_list = db.session.query(Job.id).filter(
            Job.build_id == last_build['id'],
        )

        test_durations = dict(db.session.query(
            TestCase.name, TestCase.duration
        ).filter(
            TestCase.job_id.in_(job_list),
        ))
        test_names = []
        total_count, total_duration = 0, 0
        for test in test_durations:
            test_names.append(test)
            total_duration += test_durations[test]
            total_count += 1

        test_stats = {}
        if test_names:
            sep = TestCase(name=test_names[0]).sep
            tree = build_flat_tree(test_names, sep=sep)
            for group_name, group_tests in tree.iteritems():
                segments = self._normalize_test_segments(group_name)
                test_stats[segments] = sum(test_durations[t] for t in group_tests)

        # the build report can contain different test suites so this isnt the
        # most accurate
        if total_duration > 0:
            avg_test_time = int(total_duration / total_count)
        else:
            avg_test_time = 0

        return test_stats, avg_test_time

    def _normalize_test_segments(self, test_name):
        sep = TestCase(name=test_name).sep
        segments = test_name.split(sep)

        # kill the file extension
        if sep is '/' and '.' in segments[-1]:
            segments[-1] = segments[-1].rsplit('.', 1)[0]

        return tuple(segments)

    def _shard_tests(self, tests, num_shards, test_stats, avg_test_time):
        """
        Breaks a set of tests into shards.

        Args:
            tests (list): A list of test names.
            num_shards (int): How many shards over which to distribute the tests.
            test_stats (dict): A mapping from normalized test name to duration.
            avg_test_time (int): Average duration of a single test.

        Returns:
            list: Shards. Each element is a pair containing the weight for that
                shard and the test names assigned to that shard.
        """

        def get_test_duration(test_name):
            segments = self._normalize_test_segments(test_name)
            result = test_stats.get(segments)
            if result is None:
                if test_stats:
                    self.logger.info('No existing duration found for test %r', test_name)
                result = avg_test_time
            return result

        # Each element is a pair (weight, tests).
        groups = [(0, []) for _ in range(num_shards)]
        # Groups is already a proper heap, but we'll call this to guarantee it.
        heapq.heapify(groups)
        weighted_tests = [(get_test_duration(t), t) for t in tests]
        for weight, test in sorted(weighted_tests, reverse=True):
            group_weight, group_tests = heapq.heappop(groups)
            group_weight += 1 + weight
            group_tests.append(test)
            heapq.heappush(groups, (group_weight, group_tests))

        return groups

    def _expand_jobs(self, step, artifact):
        builder = self.get_builder()
        artifact_data = builder.fetch_artifact(step, artifact.data)
        phase_config = artifact_data.json()

        assert phase_config['cmd']
        assert '{test_names}' in phase_config['cmd']
        assert phase_config['tests']

        test_stats, avg_test_time = self.get_test_stats(step.project)

        groups = self._shard_tests(phase_config['tests'], self.num_shards, test_stats, avg_test_time)

        phase, created = get_or_create(JobPhase, where={
            'job': step.job,
            'project': step.project,
            'label': phase_config.get('phase') or 'Test',
        }, defaults={
            'status': Status.queued,
        })
        db.session.commit()

        assert len(groups) == self.num_shards

        for weight, test_list in groups:
            self._expand_job(phase, {
                'tests': test_list,
                'cmd': phase_config['cmd'],
                'path': phase_config.get('path', ''),
                'weight': weight,
            })

    def _expand_job(self, phase, job_config):
        assert job_config['tests']

        test_names = ' '.join(job_config['tests'])
        label = md5(test_names).hexdigest()

        step, created = get_or_create(JobStep, where={
            'job': phase.job,
            'project': phase.project,
            'phase': phase,
            'label': label,
        }, defaults={
            'data': {
                'cmd': job_config['cmd'],
                'path': job_config['path'],
                'tests': job_config['tests'],
                'expanded': True,
                'job_name': self.job_name,
                'build_no': None,
                'weight': job_config['weight']
            },
            'status': Status.queued,
        })

        # TODO(dcramer): due to no unique constraints this section of code
        # presents a race condition when run concurrently
        if not step.data.get('build_no'):
            builder = self.get_builder()
            params = builder.get_job_parameters(
                step.job,
                changes_bid=step.id.hex,
                script=step.data['cmd'].format(
                    test_names=test_names,
                ),
                path=step.data['path'],
            )

            is_diff = not step.job.source.is_commit()
            job_data = builder.create_job_from_params(
                changes_bid=step.id.hex,
                params=params,
                job_name=step.data['job_name'],
                is_diff=is_diff
            )
            step.data.update(job_data)
            db.session.add(step)

        db.session.commit()

        sync_job_step.delay_if_needed(
            step_id=step.id.hex,
            task_id=step.id.hex,
            parent_task_id=phase.job.id.hex,
        )
