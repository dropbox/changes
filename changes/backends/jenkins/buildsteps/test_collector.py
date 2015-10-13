from __future__ import absolute_import

from flask import current_app

import heapq
import logging
import uuid

from hashlib import md5

from changes.api.client import api_client
from changes.backends.jenkins.buildsteps.collector import JenkinsCollectorBuilder, JenkinsCollectorBuildStep
from changes.buildsteps.base import BuildStep
from changes.config import db
from changes.constants import Result, Status
from changes.db.utils import get_or_create
from changes.jobs.sync_job_step import sync_job_step
from changes.models import Job, JobPhase, JobStep, TestCase
from changes.utils.agg import aggregate_result
from changes.utils.trees import build_flat_tree


class JenkinsTestCollectorBuilder(JenkinsCollectorBuilder):
    def __init__(self, shard_build_type=None, shard_setup_script=None, shard_teardown_script=None,
                 *args, **kwargs):
        self.shard_build_desc = self.load_build_desc(shard_build_type)
        self.shard_setup_script = shard_setup_script
        self.shard_teardown_script = shard_teardown_script
        super(JenkinsTestCollectorBuilder, self).__init__(*args, **kwargs)

    def can_snapshot(self):
        """
        For the case of a sharded build, whether we can snapshot or not
        is determined solely by whether the shards use lxc - the collection
        phase is irrelevant.
        """
        return self.shard_build_desc.get('can_snapshot', False)

    def get_snapshot_build_desc(self):
        """
        We use the shard-phase build description in order to build the snapshot
        since it is common that the collection phase description doesn't even
        support snapshots, and we need the distribution/release to match otherwise
        it won't be able to find the snapshot.
        """
        return self.shard_build_desc

    def get_snapshot_setup_script(self):
        """
        Generally the collection phase doesn't need to do any setup, and we wish
        to optimize the shard phase which is where the work lies, so we run the setup
        phase of the shard (generally the provisioning of an individual shard).
        """
        return self.shard_setup_script

    def get_snapshot_teardown_script(self):
        """
        Teardown is less useful for snapshot builds, but in the case that it actually
        does something useful like remove logs (of, for example, services that started
        during the snapshot build but then get killed because we destroy the container),
        this could keep the actual snapshot cleaner as the teardown is run before the
        snapshot itself is taken.
        """
        return self.shard_teardown_script

    def get_default_job_phase_label(self, job, job_data):
        return 'Collect Tests'

    def get_required_artifact(self):
        """The initial (collect) step must return at least one artifact with
        this filename, or it will be marked as failed. This logic is checked in
        JenkinsCollectorBuildStep, where it checks all artifacts to ensure
        one with this filename was collected.

        Returns:
            str: the required artifact
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
    def __init__(self, shards=None, max_shards=10, collection_build_type=None,
                 build_type=None, setup_script='', teardown_script='',
                 collection_setup_script='', collection_teardown_script='',
                 test_stats_from=None,
                 **kwargs):
        """
        Arguments:
            shards = number of shards to use
            max_shards = legacy option, same as shards
            collection_build_type = build type to use for the collection phase
            collection_setup_script = setup to use for the collection phase
            collection_teardown_script = teardown to use for the collection phase
            build_type = build type to use for the shard phase
            setup_script = setup to use for the shard phase
            teardown_script = teardown to use for the shard phase

            test_stats_from = project to get test statistics from, or
              None (the default) to use this project.  Useful if the
              project runs a different subset of tests each time, so
              test timing stats from the parent are not reliable.

        """
        # TODO(josiah): migrate existing step configs to use "shards" and remove max_shards
        if shards:
            self.max_shards = shards
        else:
            self.max_shards = max_shards

        # its fairly normal that the collection script is simple and so LXC is a waste
        # of time, so we support running the shards and the collector in different
        # environments
        self.shard_build_type = build_type

        if self.shard_build_type is None:
            self.shard_build_type = current_app.config[
                'CHANGES_CLIENT_DEFAULT_BUILD_TYPE']

        super(JenkinsTestCollectorBuildStep, self).__init__(
            build_type=collection_build_type,
            setup_script=collection_setup_script,
            teardown_script=collection_teardown_script,
            **kwargs)

        self.shard_setup_script = setup_script
        self.shard_teardown_script = teardown_script
        self.test_stats_from = test_stats_from

    def get_builder_options(self):
        options = super(JenkinsTestCollectorBuildStep, self).get_builder_options()
        options.update({
            'shard_build_type': self.shard_build_type,
            'shard_setup_script': self.shard_setup_script,
            'shard_teardown_script': self.shard_teardown_script
        })
        return options

    def get_label(self):
        return 'Collect tests from job "{0}" on Jenkins'.format(self.job_name)

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

        step_shard_counts = [step.data.get('shard_count', 1) for step in phase_steps]
        assert len(set(step_shard_counts)) == 1, "Mixed shard counts in phase!"
        shard_count = step_shard_counts[0]
        if len(phase_steps) != shard_count:
            # TODO(josiah): we'd like to be able to record a FailureReason
            # here, but currently a FailureReason must correspond to a JobStep.
            logging.error("Build failed due to incorrect number of shards: expected %d, got %d",
                          shard_count, len(phase_steps))
            return Result.unknown
        return Result.passed

    def validate_phase(self, phase):
        """Called when a job phase is ready to be finished.

        This is responsible for setting the phases's final result. We verify
        that the proper number of steps were created in the second (i.e.
        expanded) phase."""
        phase.result = aggregate_result([s.result for s in phase.current_steps] +
                                        [self._validate_shards(phase.current_steps)])

    def get_test_stats(self, project_slug):
        response = api_client.get('/projects/{project}/'.format(
            project=project_slug))
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

    def _shard_tests(self, tests, max_shards, test_stats, avg_test_time):
        """
        Breaks a set of tests into shards.

        Args:
            tests (list): A list of test names.
            max_shards (int): Maximum amount of shards over which to distribute the tests.
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

        # don't use more shards than there are tests
        num_shards = min(len(tests), max_shards)
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
        assert 'tests' in phase_config

        num_tests = len(phase_config['tests'])
        test_stats, avg_test_time = self.get_test_stats(self.test_stats_from or step.project.slug)

        phase, created = get_or_create(JobPhase, where={
            'job': step.job,
            'project': step.project,
            'label': phase_config.get('phase') or 'Test',
        }, defaults={
            'status': Status.queued
        })
        db.session.commit()

        # If there are no tests to run, the phase is done.
        if num_tests == 0:
            phase.status = Status.finished
            phase.result = Result.passed
            db.session.add(phase)
            db.session.commit()
            return

        # Check for whether a previous run of this task has already
        # created JobSteps for us, since doing it again would create a
        # double-sharded build.
        steps = JobStep.query.filter_by(phase_id=phase.id, replacement_id=None).all()
        if steps:
            step_shard_counts = [s.data.get('shard_count', 1) for s in steps]
            assert len(set(step_shard_counts)) == 1, "Mixed shard counts in phase!"
            assert len(steps) == step_shard_counts[0]
        else:
            # Create all of the job steps and commit them together.
            groups = self._shard_tests(phase_config['tests'], self.max_shards,
                                       test_stats, avg_test_time)
            steps = [
                self._create_jobstep(phase, phase_config['cmd'], phase_config.get('path', ''),
                                     weight, test_list, len(groups))
                for weight, test_list in groups
                ]
            assert len(steps) == len(groups)
            db.session.commit()

        # Now that that database transaction is done, we'll do the slow work of
        # creating jenkins builds.
        for step in steps:
            self._create_jenkins_build(step)
            sync_job_step.delay_if_needed(
                step_id=step.id.hex,
                task_id=step.id.hex,
                parent_task_id=phase.job.id.hex,
            )

    def _create_jobstep(self, phase, phase_cmd, phase_path, weight, test_list, shard_count=1, force_create=False):
        """
        Create a JobStep in the database for a single shard.

        This creates the JobStep, but does not commit the transaction.

        Args:
            phase (JobPhase): The phase this step will be part of.
            phase_cmd (str): Command configured for the collection step.
            phase_path (str): Path configured for the collection step.
            weight (int): The weight of this shard.
            test_list (list): The list of tests names for this shard.
            shard_count (int): The total number of shards in this JobStep's phase.
            force_create (bool): Force this JobStep to be created (rather than
                retrieved). This is used when replacing a JobStep to make sure
                we don't just get the old one.

        Returns:
            JobStep: the (possibly-newly-created) JobStep.
        """
        test_names = ' '.join(test_list)
        label = md5(test_names).hexdigest()

        where = {
            'job': phase.job,
            'project': phase.project,
            'phase': phase,
            'label': label,
        }
        if force_create:
            # uuid is unique so forces JobStep to be created
            where['id'] = uuid.uuid4()

        step, created = get_or_create(JobStep, where=where, defaults={
            'data': {
                'cmd': phase_cmd,
                'path': phase_path,
                'tests': test_list,
                'expanded': True,
                'shard_count': shard_count,
                'job_name': self.job_name,
                'build_no': None,
                'weight': weight,
            },
            'status': Status.queued,
        })
        assert created or not force_create
        BuildStep.handle_debug_infra_failures(step, self.debug_config, 'expanded')
        db.session.add(step)
        return step

    def create_replacement_jobstep(self, step):
        if not step.data.get('expanded'):
            return super(JenkinsTestCollectorBuildStep, self).create_replacement_jobstep(step)
        newstep = self._create_jobstep(step.phase, step.data['cmd'], step.data['path'],
                                       step.data['weight'], step.data['tests'],
                                       step.data['shard_count'], force_create=True)
        step.replacement_id = newstep.id
        db.session.add(step)
        db.session.commit()

        self._create_jenkins_build(newstep)
        sync_job_step.delay_if_needed(
            step_id=newstep.id.hex,
            task_id=newstep.id.hex,
            parent_task_id=newstep.phase.job.id.hex,
        )
        return newstep

    def _create_jenkins_build(self, step):
        """
        Create a jenkins build for the given expanded jobstep.

        If the given step already has a jenkins build associated with it, this
        will not perform any work. If not, this creates the build, updates the
        step to refer to the new build, and commits the change to the database.

        Args:
            step (JobStep): The shard we'd like to launch a jenkins build for.
        """
        # we also have to inject the correct build_type here in order
        # to generate the correct params and to generate the correct
        # commands later on
        builder = self.get_builder(build_type=self.shard_build_type)

        builder.create_jenkins_build(step, job_name=step.data['job_name'],
            script=step.data['cmd'].format(
                test_names=' '.join(step.data['tests']),
            ),
            setup_script=self.shard_setup_script,
            teardown_script=self.shard_teardown_script,
            path=step.data['path'],
        )
