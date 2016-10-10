from __future__ import absolute_import, division

from typing import Dict, List, Tuple  # NOQA

from changes.api.client import api_client
from changes.config import db, statsreporter
from changes.constants import ResultSource, SelectiveTestingPolicy
from changes.expanders.base import Expander
from changes.models.bazeltarget import BazelTarget
from changes.models.command import FutureCommand
from changes.models.job import Job
from changes.models.jobstep import FutureJobStep
from changes.utils.shards import shard


class BazelTargetsExpander(Expander):
    """
    The ``cmd`` value must exist (and contain {target_names}) as well as the
    ``affected_targets`` and ``unaffected_targets`` attribute which must be a list of strings:

        {
            "phase": "optional phase name",
            "cmd": "bazel test {target_names}",
            "path": "",
            "affected_targets": [
                "foo.bar.test_baz",
                "foo.bar.test_bar"
            ],
            "unaffected_targets": [
                "foo.other.test_baz",
                "foo.other.test_bar"
            ],
            "dependency_map": {
                "//foo/bar:test_baz": ["foo/bar/test.txt", "foo/bar/test2.txt"]
            },
            "artifact_search_path": "search path for artifact, required"
        }
    """

    def validate(self):
        for required in ['affected_targets', 'unaffected_targets', 'cmd', 'artifact_search_path']:
            assert required in self.data, 'Missing ``{}`` attribute'.format(required)
        assert '{target_names}' in self.data[
            'cmd'], 'Missing ``{target_names}`` in command'

    def expand(self, job, max_executors, test_stats_from=None):
        target_stats, avg_time = self.get_target_stats(
            test_stats_from or self.project.slug)

        affected_targets = self.data['affected_targets']
        unaffected_targets = self.data['unaffected_targets']
        all_targets = affected_targets + unaffected_targets
        statsreporter.stats().set_gauge('{}_bazel_affected_targets_count'.format(self.project.slug), len(affected_targets))
        statsreporter.stats().set_gauge('{}_bazel_all_targets_count'.format(self.project.slug), len(all_targets))
        to_shard = all_targets

        # NOTE: null values for selective testing policy implies `disabled`
        if job.build.selective_testing_policy is SelectiveTestingPolicy.enabled:
            to_shard = affected_targets
            for target in unaffected_targets:
                # TODO(naphat) should we check if the target exists in the parent revision?
                # it should be impossible for it not to exist by our collect-targets script
                target_object = BazelTarget(
                    job=job,
                    name=target,
                    result_source=ResultSource.from_parent,
                )
                db.session.add(target_object)

        groups = shard(to_shard, max_executors,
                       target_stats, avg_time)

        for weight, target_list in groups:
            future_command = FutureCommand(
                script=self.data['cmd'].format(
                    target_names=' '.join(target_list)),
                path=self.data.get('path'),
                env=self.data.get('env'),
                artifacts=self.data.get('artifacts'),
            )
            future_jobstep = FutureJobStep(
                label=self.data.get('label') or future_command.label,
                commands=[future_command],
                data={
                    'weight': weight,
                    'targets': target_list,
                    'shard_count': len(groups),
                    'artifact_search_path': self.data.get('artifact_search_path'),
                    'dependency_map': self.data.get('dependency_map', {}),
                },
            )
            yield future_jobstep

    def default_phase_name(self):
        # type: () -> str
        return 'Run test targets'

    @classmethod
    def get_target_stats(cls, project_slug):
        # type: (str) -> Tuple[Dict[str, int], int]
        """Collect the run time statistics for targets.

        Arguments:
            project_slug (str)

        Returns:
            Tuple[Dict[str, int], int]: The first item is the mapping
                from target names to run duration, in ms. The second
                item is the average run duration across all targets.
                If a target has no duration recorded, it is excluded
                from all calculations and mapping.
        """
        response = api_client.get('/projects/{project}/'.format(
            project=project_slug))
        last_build = response['lastPassingBuild']

        if not last_build:
            # use a failing build if no build has passed yet
            last_build = response['lastBuild']

        if not last_build:
            return {}, 0

        job_list = db.session.query(Job.id).filter(
            Job.build_id == last_build['id'],
        )

        if job_list:
            target_durations = dict(db.session.query(
                BazelTarget.name, BazelTarget.duration
            ).filter(
                BazelTarget.job_id.in_(job_list),
                ~BazelTarget.duration.is_(None),
            ))
        else:
            target_durations = dict()

        total_duration = sum(target_durations.itervalues())

        if total_duration > 0:
            avg_test_time = int(total_duration / len(target_durations))
        else:
            avg_test_time = 0

        return target_durations, avg_test_time
