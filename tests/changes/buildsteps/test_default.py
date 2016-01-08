from __future__ import absolute_import

import mock

from changes.buildsteps.default import (
    DEFAULT_ARTIFACTS, DEFAULT_ENV, DEFAULT_PATH, DEFAULT_RELEASE,
    DefaultBuildStep
)
from changes.config import db
from changes.constants import Result, Status, Cause
from changes.models import CommandType, FutureCommand, FutureJobStep, Repository
from changes.testutils import TestCase
from changes.vcs.base import Vcs


class DefaultBuildStepTest(TestCase):
    def get_buildstep(self, **kwargs):
        return DefaultBuildStep(commands=(
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
            dict(
                script='make snapshot',
                type='snapshot',
            ),
        ), **kwargs)

    def test_get_resource_limits(self):
        buildstep = self.get_buildstep(cpus=8, memory=9000)
        assert buildstep.get_resource_limits() == {'cpus': 8, 'memory': 9000, }

    def test_execute(self):
        build = self.create_build(self.create_project())
        job = self.create_job(build)

        buildstep = self.get_buildstep()
        buildstep.execute(job)

        step = job.phases[0].steps[0]

        assert step.data['release'] == DEFAULT_RELEASE
        assert step.status == Status.pending_allocation

        commands = step.commands
        assert len(commands) == 2

        assert commands[0].script == 'echo "hello world 2"'
        assert commands[0].cwd == '/usr/test/1'
        assert commands[0].type == CommandType.setup
        assert tuple(commands[0].artifacts) == ('artifact1.txt', 'artifact2.txt')
        assert commands[0].env['PATH'] == '/usr/test/1'
        for k, v in DEFAULT_ENV.items():
            if k != 'PATH':
                assert commands[0].env[k] == v

        assert commands[1].script == 'echo "hello world 1"'
        assert commands[1].cwd == DEFAULT_PATH
        assert commands[1].type == CommandType.default
        assert tuple(commands[1].artifacts) == tuple(DEFAULT_ARTIFACTS)
        assert commands[1].env == DEFAULT_ENV

    @mock.patch.object(Repository, 'get_vcs')
    def test_execute_collection_step(self, get_vcs):
        build = self.create_build(self.create_project())
        job = self.create_job(build)

        vcs = mock.Mock(spec=Vcs)
        vcs.get_buildstep_clone.return_value = 'git clone https://example.com'
        get_vcs.return_value = vcs

        buildstep = DefaultBuildStep(commands=[{'script': 'ls', 'type': 'collect_tests', 'path': 'subdir'},
                                               {'script': 'setup_command', 'type': 'setup'},
                                               {'script': 'default_command'},
                                               {'script': 'make snapshot', 'type': 'snapshot'}])
        buildstep.execute(job)

        step = job.phases[0].steps[0]

        assert step.data['release'] == DEFAULT_RELEASE
        assert step.status == Status.pending_allocation

        commands = step.commands
        assert len(commands) == 2

        assert commands[0].script == 'git clone https://example.com'
        assert commands[0].cwd == ''
        assert commands[0].type == CommandType.infra_setup
        assert commands[0].env == DEFAULT_ENV

        assert commands[1].script == 'ls'
        assert commands[1].cwd == './source/subdir'
        assert commands[1].type == CommandType.collect_tests
        assert tuple(commands[1].artifacts) == tuple(DEFAULT_ARTIFACTS)
        assert commands[1].env == DEFAULT_ENV

    def test_execute_snapshot(self):
        build = self.create_build(self.create_project(), cause=Cause.snapshot)
        job = self.create_job(build)

        buildstep = DefaultBuildStep(commands=[{'script': 'ls', 'type': 'collect_tests'},
                                               {'script': 'setup_command', 'type': 'setup'},
                                               {'script': 'default_command'},
                                               {'script': 'make snapshot', 'type': 'snapshot'}])
        buildstep.execute(job)

        step = job.phases[0].steps[0]

        assert step.data['release'] == DEFAULT_RELEASE
        assert step.status == Status.pending_allocation

        # collect tests and default commands shouldn't be added
        commands = step.commands
        assert len(commands) == 2

        assert commands[0].script == 'setup_command'
        assert commands[0].cwd == DEFAULT_PATH
        assert commands[0].type == CommandType.setup
        assert tuple(commands[0].artifacts) == tuple(DEFAULT_ARTIFACTS)
        assert commands[1].env == DEFAULT_ENV

        assert commands[1].script == 'make snapshot'
        assert commands[1].cwd == DEFAULT_PATH
        assert commands[1].type == CommandType.snapshot
        assert tuple(commands[1].artifacts) == tuple(DEFAULT_ARTIFACTS)
        assert commands[1].env == DEFAULT_ENV

    def test_create_replacement_jobstep(self):
        build = self.create_build(self.create_project())
        job = self.create_job(build)

        buildstep = self.get_buildstep()
        buildstep.execute(job)

        oldstep = job.phases[0].steps[0]
        oldstep.result = Result.infra_failed
        oldstep.status = Status.finished
        db.session.add(oldstep)
        db.session.commit()

        step = buildstep.create_replacement_jobstep(oldstep)
        # new jobstep should still be part of same job/phase
        assert step.job == job
        assert step.phase == oldstep.phase
        # make sure .steps actually includes the new jobstep
        assert len(oldstep.phase.steps) == 2
        # make sure replacement id is correctly set
        assert oldstep.replacement_id == step.id

        # we want the retried jobstep to have the exact same attributes the
        # original jobstep would be expected to after execute()
        assert step.data['release'] == DEFAULT_RELEASE
        assert step.status == Status.pending_allocation

        commands = step.commands
        assert len(commands) == 2

        assert commands[0].script == 'echo "hello world 2"'
        assert commands[0].cwd == '/usr/test/1'
        assert commands[0].type == CommandType.setup
        assert tuple(commands[0].artifacts) == ('artifact1.txt', 'artifact2.txt')
        assert commands[0].env['PATH'] == '/usr/test/1'
        for k, v in DEFAULT_ENV.items():
            if k != 'PATH':
                assert commands[0].env[k] == v

        assert commands[1].script == 'echo "hello world 1"'
        assert commands[1].cwd == DEFAULT_PATH
        assert commands[1].type == CommandType.default
        assert tuple(commands[1].artifacts) == tuple(DEFAULT_ARTIFACTS)
        assert commands[1].env == DEFAULT_ENV

    @mock.patch.object(Repository, 'get_vcs')
    def test_create_expanded_jobstep(self, get_vcs):
        build = self.create_build(self.create_project())
        job = self.create_job(build)
        jobphase = self.create_jobphase(job, label='foo')
        jobstep = self.create_jobstep(jobphase)

        new_jobphase = self.create_jobphase(job, label='bar')

        vcs = mock.Mock(spec=Vcs)
        vcs.get_buildstep_clone.return_value = 'git clone https://example.com'
        get_vcs.return_value = vcs

        future_jobstep = FutureJobStep(
            label='test',
            commands=[
                FutureCommand('echo 1'),
                FutureCommand('echo "foo"\necho "bar"', path='subdir'),
            ],
        )

        buildstep = self.get_buildstep()
        new_jobstep = buildstep.create_expanded_jobstep(
            jobstep, new_jobphase, future_jobstep)

        db.session.flush()

        assert new_jobstep.data['expanded'] is True

        commands = new_jobstep.commands

        assert len(commands) == 4
        assert commands[0].script == 'git clone https://example.com'
        assert commands[0].cwd == ''
        assert commands[0].type == CommandType.infra_setup
        assert commands[0].order == 0
        assert commands[1].script == 'echo "hello world 2"'
        assert commands[1].cwd == '/usr/test/1'
        assert commands[1].type == CommandType.setup
        assert tuple(commands[1].artifacts) == ('artifact1.txt', 'artifact2.txt')
        assert commands[1].order == 1
        assert commands[2].label == 'echo 1'
        assert commands[2].script == 'echo 1'
        assert commands[2].order == 2
        assert commands[2].cwd == DEFAULT_PATH
        assert commands[2].type == CommandType.default
        assert tuple(commands[2].artifacts) == tuple(DEFAULT_ARTIFACTS)
        assert commands[3].label == 'echo "foo"'
        assert commands[3].script == 'echo "foo"\necho "bar"'
        assert commands[3].order == 3
        assert commands[3].cwd == './source/subdir'
        assert commands[3].type == CommandType.default
        assert tuple(commands[3].artifacts) == tuple(DEFAULT_ARTIFACTS)

    @mock.patch.object(Repository, 'get_vcs')
    def test_create_replacement_jobstep_expanded(self, get_vcs):
        build = self.create_build(self.create_project())
        job = self.create_job(build)
        jobphase = self.create_jobphase(job, label='foo')
        jobstep = self.create_jobstep(jobphase)

        new_jobphase = self.create_jobphase(job, label='bar')

        vcs = mock.Mock(spec=Vcs)
        vcs.get_buildstep_clone.return_value = 'git clone https://example.com'
        get_vcs.return_value = vcs

        future_jobstep = FutureJobStep(
            label='test',
            commands=[
                FutureCommand('echo 1'),
                FutureCommand('echo "foo"\necho "bar"', path='subdir'),
            ],
            data={'weight': 1, 'forceInfraFailure': True},
        )

        buildstep = self.get_buildstep()
        fail_jobstep = buildstep.create_expanded_jobstep(
            jobstep, new_jobphase, future_jobstep)

        fail_jobstep.result = Result.infra_failed
        fail_jobstep.status = Status.finished
        db.session.add(fail_jobstep)
        db.session.commit()

        new_jobstep = buildstep.create_replacement_jobstep(fail_jobstep)
        # new jobstep should still be part of same job/phase
        assert new_jobstep.job == job
        assert new_jobstep.phase == fail_jobstep.phase
        # make sure .steps actually includes the new jobstep
        assert len(fail_jobstep.phase.steps) == 2
        # make sure replacement id is correctly set
        assert fail_jobstep.replacement_id == new_jobstep.id

        # we want the replacement jobstep to have the same attributes the
        # original jobstep would be expected to after expand_jobstep()
        assert new_jobstep.data['expanded'] is True
        assert new_jobstep.data['weight'] == 1
        # make sure non-whitelisted attributes aren't copied over
        assert 'forceInfraFailure' not in new_jobstep.data

        commands = new_jobstep.commands

        assert len(commands) == 4
        assert commands[0].script == 'git clone https://example.com'
        assert commands[0].cwd == ''
        assert commands[0].type == CommandType.infra_setup
        assert commands[0].order == 0
        assert commands[1].script == 'echo "hello world 2"'
        assert commands[1].cwd == '/usr/test/1'
        assert commands[1].type == CommandType.setup
        assert tuple(commands[1].artifacts) == ('artifact1.txt', 'artifact2.txt')
        assert commands[1].order == 1
        assert commands[2].label == 'echo 1'
        assert commands[2].script == 'echo 1'
        assert commands[2].order == 2
        assert commands[2].cwd == DEFAULT_PATH
        assert commands[2].type == CommandType.default
        assert tuple(commands[2].artifacts) == tuple(DEFAULT_ARTIFACTS)
        assert commands[3].label == 'echo "foo"'
        assert commands[3].script == 'echo "foo"\necho "bar"'
        assert commands[3].order == 3
        assert commands[3].cwd == './source/subdir'
        assert commands[3].type == CommandType.default
        assert tuple(commands[3].artifacts) == tuple(DEFAULT_ARTIFACTS)

    def test_get_allocation_params(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)

        buildstep = self.get_buildstep()
        result = buildstep.get_allocation_params(jobstep)
        assert result == {
            'adapter': 'basic',
            'server': 'http://example.com/api/0/',
            'jobstep_id': jobstep.id.hex,
            'release': 'precise',
            's3-bucket': 'snapshot-bucket',
            'pre-launch': 'echo pre',
            'post-launch': 'echo post',
            'artifacts-server': 'http://localhost:1234',
            'artifact-search-path': DEFAULT_PATH,
        }

    def test_test_get_allocation_params_for_snapshotting(self):
        project = self.create_project()
        build = self.create_build(project)
        plan = self.create_plan(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)
        snapshot = self.create_snapshot(project)
        image = self.create_snapshot_image(snapshot, plan, job=job)

        buildstep = self.get_buildstep()
        result = buildstep.get_allocation_params(jobstep)
        assert result['save-snapshot'] == image.id.hex
