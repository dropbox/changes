from __future__ import absolute_import

from operator import itemgetter

from changes.api.client import api_client
from changes.config import db
from changes.expanders.base import Expander
from changes.models import FutureCommand, FutureJobStep, Job, TestCase
from changes.utils.trees import build_flat_tree


class TestsExpander(Expander):
    """
    The ``command`` value must exist (and contain {test_names}) as well as the
    ``tests`` attribute which must be a list of strings:

        {
            "phase": "optional phase name",
            "command": "py.test --junit=junit.xml {test_names}",
            "path": "",
            "tests": [
                "foo.bar.test_baz",
                "foo.bar.test_bar"
            ]
        }
    """
    def validate(self):
        assert 'tests' in self.data, 'Missing ``tests`` attribute'
        assert 'command' in self.data, 'Missing ``command`` attribute'
        assert '{test_names}' in self.data['command'], 'Missing ``{test_names}`` in command'

    def expand(self, max_executors):
        test_stats, avg_test_time = self.get_test_stats()

        group_tests = [[] for _ in range(max_executors)]
        group_weights = [0 for _ in range(max_executors)]
        weights = [0] * max_executors
        weighted_tests = [
            (self.get_test_duration(t, test_stats) or avg_test_time, t)
            for t in self.data['tests']
        ]
        for weight, test in sorted(weighted_tests, reverse=True):
            low_index, _ = min(enumerate(weights), key=itemgetter(1))
            weights[low_index] += 1 + weight
            group_tests[low_index].append(test)
            group_weights[low_index] += 1 + weight

        for test_list, weight in zip(group_tests, group_weights):
            future_command = FutureCommand(
                script=self.data['command'].format(test_names=' '.join(test_list)),
                path=self.data.get('path'),
                env=self.data.get('env'),
                artifacts=self.data.get('artifacts'),
            )
            future_jobstep = FutureJobStep(
                label=self.data.get('label') or future_command.label,
                commands=[future_command],
                data={'weight': weight},
            )
            yield future_jobstep

    def get_test_duration(self, test_name, test_stats):
        segments = self.normalize_test_segments(test_name)
        result = test_stats.get(segments)
        if result is None:
            if test_stats:
                self.logger.info('No existing duration found for test %r', test_name)
        return result

    def get_test_stats(self):
        response = api_client.get('/projects/{project}/'.format(
            project=self.project.slug))
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
                segments = self.normalize_test_segments(group_name)
                test_stats[segments] = sum(test_durations[t] for t in group_tests)

        # the build report can contain different test suites so this isnt the
        # most accurate
        if total_duration > 0:
            avg_test_time = int(total_duration / total_count)
        else:
            avg_test_time = 0

        return test_stats, avg_test_time

    def normalize_test_segments(self, test_name):
        sep = TestCase(name=test_name).sep
        segments = test_name.split(sep)

        # kill the file extension
        if sep is '/' and '.' in segments[-1]:
            segments[-1] = segments[-1].rsplit('.', 1)[0]

        return tuple(segments)
