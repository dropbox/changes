from __future__ import absolute_import

from changes.buildsteps.default import (
    DEFAULT_ARTIFACTS, DEFAULT_ENV, DEFAULT_PATH,
)
from changes.buildsteps.lxc import LXCBuildStep
from changes.constants import Status
from changes.models.command import CommandType
from changes.testutils import TestCase


class LXCBuildStepTest(TestCase):
    def get_buildstep(self, **kwargs):
        kwargs['release'] = 'trusty'
        kwargs['cpus'] = 8
        kwargs['memory'] = 9000
        return LXCBuildStep(
            commands=[
                dict(
                    script='echo "hello world 2"',
                    path='/usr/test/1',
                    artifacts=['artifact1.txt', 'artifact2.txt'],
                    env={'PATH': '/usr/test/1'},
                    type='setup',
                ),
                dict(
                    script='echo "hello world 1"',
                ),
            ], **kwargs)

    def test_execute(self):
        build = self.create_build(self.create_project(name='foo'), label='buildlabel')
        job = self.create_job(build)

        buildstep = self.get_buildstep(cluster='foo', repo_path='source', path='tests')
        buildstep.execute(job)

        assert job.phases[0].label == 'buildlabel'
        step = job.phases[0].steps[0]

        assert step.data['release'] == 'trusty'
        assert step.status == Status.pending_allocation
        assert step.cluster == 'foo'
        assert step.label == 'buildlabel'

        commands = step.commands
        assert len(commands) == 3

        idx = 0
        # blacklist remove command
        assert commands[idx].script == '/var/changes/input/blacklist-remove "foo.yaml"'
        assert commands[idx].cwd == 'source'
        assert commands[idx].type == CommandType.infra_setup
        assert commands[idx].artifacts == []
        assert commands[idx].env == DEFAULT_ENV
        assert commands[idx].order == idx

        idx += 1
        assert commands[idx].script == 'echo "hello world 2"'
        assert commands[idx].cwd == '/usr/test/1'
        assert commands[idx].type == CommandType.setup
        assert tuple(commands[idx].artifacts) == ('artifact1.txt', 'artifact2.txt')
        assert commands[idx].env['PATH'] == '/usr/test/1'
        for k, v in DEFAULT_ENV.items():
            if k != 'PATH':
                assert commands[idx].env[k] == v

        idx += 1
        assert commands[idx].script == 'echo "hello world 1"'
        assert commands[idx].cwd == 'source/tests'
        assert commands[idx].type == CommandType.default
        assert tuple(commands[idx].artifacts) == tuple(DEFAULT_ARTIFACTS)
        assert commands[idx].env == DEFAULT_ENV

    def test_get_allocation_params(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)

        buildstep = self.get_buildstep()
        result = buildstep.get_allocation_params(jobstep)
        assert result == {
            'adapter': 'lxc',
            'server': 'http://changes-int.example.com/api/0/',
            'jobstep_id': jobstep.id.hex,
            'release': 'trusty',
            's3-bucket': 'snapshot-bucket',
            'pre-launch': 'echo pre',
            'post-launch': 'echo post',
            'memory': '9000',
            'cpus': '8',
            'artifacts-server': 'http://localhost:1234',
            'artifact-search-path': DEFAULT_PATH,
            'artifact-suffix': '',
            'use-external-env': 'false',
            'dist': 'ubuntu',
            'use-path-in-artifact-name': 'false',
        }
