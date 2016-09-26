from __future__ import absolute_import

from typing import Dict, List, Tuple  # NOQA

from changes.api.client import api_client
from changes.config import db
from changes.expanders.base import Expander
from changes.models.command import FutureCommand
from changes.models.job import Job
from changes.models.jobstep import FutureJobStep
from changes.models.test import TestCase
from changes.utils.shards import shard
from changes.utils.trees import build_flat_tree


class TestsExpander(Expander):
    """
    The ``cmd`` value must exist (and contain {test_names}) as well as the
    ``tests`` attribute which must be a list of strings:

        {
            "phase": "optional phase name",
            "cmd": "py.test --junit=junit.xml {test_names}",
            "path": "",
            "tests": [
                "foo.bar.test_baz",
                "foo.bar.test_bar"
            ]
        }
    """
    def validate(self):
        assert 'tests' in self.data, 'Missing ``tests`` attribute'
        assert 'cmd' in self.data, 'Missing ``cmd`` attribute'
        assert '{test_names}' in self.data['cmd'], 'Missing ``{test_names}`` in command'

    def expand(self, job, max_executors, test_stats_from=None):
        test_stats, avg_test_time = self.get_test_stats(test_stats_from or self.project.slug)

        groups = shard(
            self.data['tests'],
            max_executors,
            test_stats,
            avg_test_time,
            normalize_object_name=self._normalize_test_segments
        )

        for weight, test_list in groups:
            future_command = FutureCommand(
                script=self.data['cmd'].format(test_names=' '.join(test_list)),
                path=self.data.get('path'),
                env=self.data.get('env'),
                artifacts=self.data.get('artifacts'),
            )
            artifact_search_path = self.data.get('artifact_search_path')
            artifact_search_path = artifact_search_path if artifact_search_path else None
            future_jobstep = FutureJobStep(
                label=self.data.get('label') or future_command.label,
                commands=[future_command],
                data={
                    'weight': weight,
                    'tests': test_list,
                    'shard_count': len(groups),
                    'artifact_search_path': artifact_search_path,
                },
            )
            yield future_jobstep

    def default_phase_name(self):
        # type: () -> str
        return 'Run tests'

    @classmethod
    def get_test_stats(cls, project_slug):
        response = api_client.get('/projects/{project}/'.format(
            project=project_slug))
        last_build = response['lastPassingBuild']

        if not last_build:
            # use a failing build if no build has passed yet
            last_build = response['lastBuild']

        if not last_build:
            return {}, 0

        # XXX(dcramer): ideally this would be abstracted via an API
        job_list = db.session.query(Job.id).filter(
            Job.build_id == last_build['id'],
        )

        if job_list:
            test_durations = dict(db.session.query(
                TestCase.name, TestCase.duration
            ).filter(
                TestCase.job_id.in_(job_list),
            ))
        else:
            test_durations = dict()

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
                segments = cls._normalize_test_segments(group_name)
                test_stats[segments] = sum(test_durations[t] for t in group_tests)

        # the build report can contain different test suites so this isnt the
        # most accurate
        if total_duration > 0:
            avg_test_time = int(total_duration / total_count)
        else:
            avg_test_time = 0

        return test_stats, avg_test_time

    @classmethod
    def _normalize_test_segments(cls, test_name):
        sep = TestCase(name=test_name).sep
        segments = test_name.split(sep)

        # kill the file extension
        if sep is '/' and '.' in segments[-1]:
            segments[-1] = segments[-1].rsplit('.', 1)[0]

        return tuple(segments)
