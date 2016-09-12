from __future__ import absolute_import

from typing import Dict, List, Tuple  # NOQA

from changes.api.client import api_client
from changes.config import db
from changes.expanders.base import Expander
from changes.models.bazeltarget import BazelTarget
from changes.models.command import FutureCommand
from changes.models.job import Job
from changes.models.jobstep import FutureJobStep
from changes.utils.shards import shard


class BazelTargetsExpander(Expander):
    """
    The ``cmd`` value must exist (and contain {target_names}) as well as the
    ``targets`` attribute which must be a list of strings:

        {
            "phase": "optional phase name",
            "cmd": "bazel test {target_names}",
            "path": "",
            "targets": [
                "foo.bar.test_baz",
                "foo.bar.test_bar"
            ],
            "artifact_search_path": "search path for artifact, required"
        }
    """

    def validate(self):
        assert 'targets' in self.data, 'Missing ``targets`` attribute'
        assert 'cmd' in self.data, 'Missing ``cmd`` attribute'
        assert '{target_names}' in self.data[
            'cmd'], 'Missing ``{target_names}`` in command'
        assert 'artifact_search_path' in self.data, 'Missing ``artifact_search_path`` attribute'

    def expand(self, max_executors, target_stats_from=None):
        target_stats, avg_time = self.get_target_stats(
            target_stats_from or self.project.slug)

        groups = shard(self.data['targets'], max_executors,
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
