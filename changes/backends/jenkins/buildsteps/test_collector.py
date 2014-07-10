from __future__ import absolute_import

import itertools

from hashlib import md5
from operator import itemgetter

from changes.api.client import api_client
from changes.backends.jenkins.buildsteps.collector import (
    JenkinsCollectorBuilder, JenkinsCollectorBuildStep
)
from changes.config import db
from changes.constants import Result, Status
from changes.db.utils import get_or_create, try_create
from changes.jobs.sync_job_step import sync_job_step
from changes.models import FailureReason, Job, JobPhase, JobStep, TestCase
from changes.utils.trees import build_flat_tree


class JenkinsTestCollectorBuilder(JenkinsCollectorBuilder):
    def get_default_job_phase_label(self, job, job_data):
        return 'Collect Tests'


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
    def __init__(self, max_shards=10, **kwargs):
        self.max_shards = max_shards
        super(JenkinsTestCollectorBuildStep, self).__init__(**kwargs)

    def get_label(self):
        return 'Collect tests from job "{0}" on Jenkins'.format(self.job_name)

    def fetch_artifact(self, step, artifact, **kwargs):
        if artifact['fileName'].endswith('tests.json'):
            self._expand_jobs(step, artifact)
        else:
            builder = self.get_builder()
            builder.sync_artifact(step, artifact, **kwargs)

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
                test_stats[group_name] = sum(test_durations[t] for t in group_tests)

        # the build report can contain different test suites so this isnt the
        # most accurate
        if total_duration > 0:
            avg_test_time = int(total_duration / total_count)
        else:
            avg_test_time = 0

        return test_stats, avg_test_time

    def _sync_results(self, step, item):
        super(JenkinsTestCollectorBuilder, self)._sync_results(step, item)

        if step.data.get('expanded'):
            return

        artifacts = item.get('artifacts', ())
        if not any(a['fileName'].endswith('tests.json') for a in artifacts):
            step.result = Result.failed
            db.session.add(step)

            job = step.job
            try_create(FailureReason, {
                'step_id': step.id,
                'job_id': job.id,
                'build_id': job.build_id,
                'project_id': job.project_id,
                'reason': 'missing_artifact'
            })

    def _expand_jobs(self, step, artifact):
        builder = self.get_builder()
        artifact_data = builder.fetch_artifact(step, artifact)
        phase_config = artifact_data.json()

        assert phase_config['cmd']
        assert '{test_names}' in phase_config['cmd']
        assert phase_config['tests']

        test_stats, avg_test_time = self.get_test_stats(step.project)

        def get_test_duration(test):
            result = test_stats.get(test)
            if result is None:
                if test_stats:
                    self.logger.info('No existing duration found for test %r', test)
                result = avg_test_time
            return result

        group_tests = [[] for _ in range(self.max_shards)]
        group_weights = [0 for _ in range(self.max_shards)]
        weights = [0] * self.max_shards
        weighted_tests = [(get_test_duration(t), t) for t in phase_config['tests']]
        for weight, test in sorted(weighted_tests, reverse=True):
            low_index, _ = min(enumerate(weights), key=itemgetter(1))
            weights[low_index] += 1 + weight
            group_tests[low_index].append(test)
            group_weights[low_index] += 1 + weight

        phase, created = get_or_create(JobPhase, where={
            'job': step.job,
            'project': step.project,
            'label': phase_config.get('phase') or 'Test',
        }, defaults={
            'status': Status.queued,
        })
        db.session.commit()

        for test_list, weight in itertools.izip(group_tests, group_weights):
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
                script=step.data['cmd'].format(
                    test_names=test_names,
                ),
                target_id=step.id.hex,
                path=step.data['path'],
            )

            job_data = builder.create_job_from_params(
                target_id=step.id.hex,
                params=params,
                job_name=step.data['job_name'],
            )
            step.data.update(job_data)
            db.session.add(step)

        db.session.commit()

        sync_job_step.delay_if_needed(
            step_id=step.id.hex,
            task_id=step.id.hex,
            parent_task_id=phase.job.id.hex,
        )
