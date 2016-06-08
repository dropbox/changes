from __future__ import absolute_import

import mock

from flask import current_app

from changes.buildsteps.default import (
    DEFAULT_ARTIFACTS, DEFAULT_ENV, DEFAULT_PATH, DEFAULT_RELEASE,
    DefaultBuildStep
)
from changes.config import db
from changes.constants import Result, Status, Cause
from changes.models.command import CommandType, FutureCommand
from changes.models.jobstep import FutureJobStep
from changes.models.repository import Repository
from changes.testutils import TestCase
from changes.vcs.base import Vcs
from changes.vcs.git import GitVcs
from changes.vcs.hg import MercurialVcs


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

    def test_invalid_other_repos(self):
        # dict instead of a list
        with self.assertRaises(ValueError):
            self.get_buildstep(other_repos={})

        # list elements aren't dicts
        with self.assertRaises(ValueError):
            self.get_buildstep(other_repos=[[]])

        # didn't specify repo and path
        with self.assertRaises(ValueError):
            self.get_buildstep(other_repos=[{'revision': 'foo'}])

    def test_execute(self):
        build = self.create_build(self.create_project(name='foo'), label='buildlabel')
        job = self.create_job(build)

        buildstep = self.get_buildstep(cluster='foo', repo_path='source', path='tests')
        buildstep.execute(job)

        assert job.phases[0].label == 'buildlabel'
        step = job.phases[0].steps[0]

        assert step.data['release'] == DEFAULT_RELEASE
        assert step.status == Status.pending_allocation
        assert step.cluster == 'foo'
        assert step.label == 'buildlabel'

        commands = step.commands
        assert len(commands) == 3

        idx = 0
        # blacklist remove command
        assert commands[idx].script == 'blacklist-remove "foo.yaml"'
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

    @mock.patch.object(Repository, 'get_vcs')
    def test_execute_collection_step(self, get_vcs):
        build = self.create_build(self.create_project(), label='buildlabel')
        job = self.create_job(build)

        vcs = mock.Mock(spec=Vcs)
        vcs.get_buildstep_clone.return_value = 'git clone https://example.com'
        get_vcs.return_value = vcs

        buildstep = DefaultBuildStep(commands=[{'script': 'ls', 'type': 'collect_tests', 'path': 'subdir'},
                                               {'script': 'setup_command', 'type': 'setup'},
                                               {'script': 'default_command'},
                                               {'script': 'make snapshot', 'type': 'snapshot'}],
                                     repo_path='source', path='tests')
        buildstep.execute(job)

        vcs.get_buildstep_clone.assert_called_with(job.source, 'source', True, None)

        assert job.phases[0].label == 'Collect tests'
        step = job.phases[0].steps[0]

        assert step.data['release'] == DEFAULT_RELEASE
        assert step.status == Status.pending_allocation
        assert step.cluster is None
        assert step.label == 'Collect tests'

        commands = step.commands
        assert len(commands) == 3

        idx = 0
        assert commands[idx].script == 'git clone https://example.com'
        assert commands[idx].cwd == ''
        assert commands[idx].type == CommandType.infra_setup
        assert commands[idx].env == DEFAULT_ENV

        # skip blacklist removal command
        idx += 1

        idx += 1
        assert commands[idx].script == 'ls'
        assert commands[idx].cwd == 'source/tests/subdir'
        assert commands[idx].type == CommandType.collect_tests
        assert tuple(commands[idx].artifacts) == tuple(DEFAULT_ARTIFACTS)
        assert commands[idx].env == DEFAULT_ENV

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
        assert step.cluster is None

        # collect tests and default commands shouldn't be added
        commands = step.commands
        assert len(commands) == 3

        # skip blacklist removal command
        idx = 1

        assert commands[idx].script == 'setup_command'
        assert commands[idx].cwd == DEFAULT_PATH
        assert commands[idx].type == CommandType.setup
        assert tuple(commands[idx].artifacts) == tuple(DEFAULT_ARTIFACTS)
        assert commands[idx].env == DEFAULT_ENV

        idx += 1
        assert commands[idx].script == 'make snapshot'
        assert commands[idx].cwd == DEFAULT_PATH
        assert commands[idx].type == CommandType.snapshot
        assert tuple(commands[idx].artifacts) == tuple(DEFAULT_ARTIFACTS)
        assert commands[idx].env == DEFAULT_ENV

    @mock.patch.object(Repository, 'get_vcs')
    @mock.patch.object(MercurialVcs, 'get_clone_command')
    @mock.patch.object(GitVcs, 'get_clone_command')
    def test_execute_other_repos(self, git_get_clone_command, mercurial_get_clone_command, get_vcs):
        build = self.create_build(self.create_project(), label='buildlabel')
        job = self.create_job(build)

        vcs = mock.Mock(spec=Vcs)
        vcs.get_buildstep_clone.return_value = 'git clone https://example.com'
        get_vcs.return_value = vcs

        git_get_clone_command.return_value = 'git clone'
        mercurial_get_clone_command.return_value = 'hg clone'

        current_app.config['GIT_DEFAULT_BASE_URI'] = 'git@giturl.com:'
        current_app.config['MERCURIAL_DEFAULT_BASE_URI'] = 'hg@hgurl.com/'
        buildstep = DefaultBuildStep(commands=[{'script': 'ls'}],
                                     repo_path='source', path='tests',
                                     other_repos=[{'repo': 'changes.git', 'path': 'changes', 'revision': 'abcdefg'},
                                                  {'repo': 'hg_repo', 'path': '/mercurial_repo', 'backend': 'hg'},
                                                  {'repo': 'git@example.com:foo.git', 'path': '/foo', 'backend': 'git'}])
        buildstep.execute(job)

        vcs.get_buildstep_clone.assert_called_with(job.source, 'source', True, None)

        git_get_clone_command.assert_any_call('git@giturl.com:changes.git', 'changes', 'abcdefg', True, None)
        git_get_clone_command.assert_any_call('git@example.com:foo.git', '/foo', 'origin/master', True, None)
        mercurial_get_clone_command.assert_any_call('hg@hgurl.com/hg_repo', '/mercurial_repo', 'default', True, None)

        assert job.phases[0].label == 'buildlabel'
        step = job.phases[0].steps[0]

        commands = step.commands
        assert len(commands) == 6

        idx = 0
        assert commands[idx].script == 'git clone https://example.com'
        assert commands[idx].cwd == ''
        assert commands[idx].type == CommandType.infra_setup
        assert commands[idx].env == DEFAULT_ENV

        for i in xrange(idx, idx + 3):
            assert commands[idx].type == CommandType.infra_setup
        idx += 3

        # skip blacklist removal command
        idx += 1

        idx += 1
        assert commands[idx].script == 'ls'

    def test_create_replacement_jobstep(self):
        build = self.create_build(self.create_project())
        job = self.create_job(build)

        buildstep = self.get_buildstep(cluster='foo')
        buildstep.execute(job)

        oldstep = job.phases[0].steps[0]
        oldstep.result = Result.infra_failed
        oldstep.status = Status.finished
        oldstep.node = self.create_node(label='ip-127-0-0-1')
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
        assert step.data['avoid_node'] == 'ip-127-0-0-1'

        # we want the retried jobstep to have the exact same attributes the
        # original jobstep would be expected to after execute()
        assert step.data['release'] == DEFAULT_RELEASE
        assert step.status == Status.pending_allocation
        assert step.cluster == 'foo'

        commands = step.commands
        assert len(commands) == 3

        # skip blacklist removal command
        idx = 1
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
        assert commands[idx].cwd == DEFAULT_PATH
        assert commands[idx].type == CommandType.default
        assert tuple(commands[idx].artifacts) == tuple(DEFAULT_ARTIFACTS)
        assert commands[idx].env == DEFAULT_ENV

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

        buildstep = self.get_buildstep(cluster='foo')
        new_jobstep = buildstep.create_expanded_jobstep(
            jobstep, new_jobphase, future_jobstep)

        db.session.flush()

        assert new_jobstep.data['expanded'] is True
        assert new_jobstep.cluster == 'foo'

        commands = new_jobstep.commands

        assert len(commands) == 5

        idx = 0
        assert commands[idx].script == 'git clone https://example.com'
        assert commands[idx].cwd == ''
        assert commands[idx].type == CommandType.infra_setup
        assert commands[idx].artifacts == []
        assert commands[idx].env == DEFAULT_ENV
        assert commands[idx].order == idx

        # skip blacklist removal command
        idx += 1

        idx += 1
        assert commands[idx].script == 'echo "hello world 2"'
        assert commands[idx].cwd == '/usr/test/1'
        assert commands[idx].type == CommandType.setup
        assert tuple(commands[idx].artifacts) == ('artifact1.txt', 'artifact2.txt')
        assert commands[idx].env['PATH'] == '/usr/test/1'
        for k, v in DEFAULT_ENV.items():
            if k != 'PATH':
                assert commands[idx].env[k] == v
        assert commands[idx].order == idx

        idx += 1
        assert commands[idx].label == 'echo 1'
        assert commands[idx].script == 'echo 1'
        assert commands[idx].order == idx
        assert commands[idx].cwd == DEFAULT_PATH
        assert commands[idx].type == CommandType.default
        assert tuple(commands[idx].artifacts) == tuple(DEFAULT_ARTIFACTS)
        assert commands[idx].env == DEFAULT_ENV

        idx += 1
        assert commands[idx].label == 'echo "foo"'
        assert commands[idx].script == 'echo "foo"\necho "bar"'
        assert commands[idx].order == idx
        assert commands[idx].cwd == './source/subdir'
        assert commands[idx].type == CommandType.default
        assert tuple(commands[idx].artifacts) == tuple(DEFAULT_ARTIFACTS)
        assert commands[idx].env == DEFAULT_ENV

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

        buildstep = self.get_buildstep(cluster='foo')
        fail_jobstep = buildstep.create_expanded_jobstep(
            jobstep, new_jobphase, future_jobstep)

        fail_jobstep.result = Result.infra_failed
        fail_jobstep.status = Status.finished
        fail_jobstep.node = self.create_node(label='ip-127-0-0-1')
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
        assert new_jobstep.data['avoid_node'] == 'ip-127-0-0-1'

        # we want the replacement jobstep to have the same attributes the
        # original jobstep would be expected to after expand_jobstep()
        assert new_jobstep.data['expanded'] is True
        assert new_jobstep.data['weight'] == 1
        assert new_jobstep.cluster == 'foo'
        # make sure non-whitelisted attributes aren't copied over
        assert 'forceInfraFailure' not in new_jobstep.data

        commands = new_jobstep.commands

        assert len(commands) == 5

        idx = 0
        assert commands[idx].script == 'git clone https://example.com'
        assert commands[idx].cwd == ''
        assert commands[idx].type == CommandType.infra_setup
        assert commands[idx].artifacts == []
        assert commands[idx].env == DEFAULT_ENV
        assert commands[idx].order == idx

        # skip blacklist removal command
        idx += 1

        idx += 1
        assert commands[idx].script == 'echo "hello world 2"'
        assert commands[idx].cwd == '/usr/test/1'
        assert commands[idx].type == CommandType.setup
        assert tuple(commands[idx].artifacts) == ('artifact1.txt', 'artifact2.txt')
        assert commands[idx].env['PATH'] == '/usr/test/1'
        for k, v in DEFAULT_ENV.items():
            if k != 'PATH':
                assert commands[idx].env[k] == v
        assert commands[idx].order == idx

        idx += 1
        assert commands[idx].label == 'echo 1'
        assert commands[idx].script == 'echo 1'
        assert commands[idx].order == idx
        assert commands[idx].cwd == DEFAULT_PATH
        assert commands[idx].type == CommandType.default
        assert tuple(commands[idx].artifacts) == tuple(DEFAULT_ARTIFACTS)
        assert commands[idx].env == DEFAULT_ENV

        idx += 1
        assert commands[idx].label == 'echo "foo"'
        assert commands[idx].script == 'echo "foo"\necho "bar"'
        assert commands[idx].order == idx
        assert commands[idx].cwd == './source/subdir'
        assert commands[idx].type == CommandType.default
        assert tuple(commands[idx].artifacts) == tuple(DEFAULT_ARTIFACTS)
        assert commands[idx].env == DEFAULT_ENV

    def test_get_allocation_params(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)

        buildstep = self.get_buildstep(repo_path='source', path='tests')
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
            'artifact-search-path': 'source/tests',
            'use-external-env': 'false',
            'dist': 'ubuntu',
        }

    def test_get_allocation_params_for_snapshotting(self):
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

    @mock.patch.object(DefaultBuildStep, 'get_allocation_params')
    def test_get_allocation_command(self, get_allocation_params):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)

        get_allocation_params.return_value = {'foo': 'bar'}
        buildstep = self.get_buildstep()
        result = buildstep.get_allocation_command(jobstep)
        assert result == 'changes-client -foo=bar'

    def test_repo_path_and_path(self):
        buildstep = self.get_buildstep()
        assert buildstep.path == DEFAULT_PATH
        assert buildstep.repo_path == DEFAULT_PATH

        buildstep = self.get_buildstep(path='foo')
        assert buildstep.path == 'foo'
        assert buildstep.repo_path == 'foo'

        buildstep = self.get_buildstep(repo_path='foo')
        assert buildstep.path == 'foo'
        assert buildstep.repo_path == 'foo'

        buildstep = self.get_buildstep(repo_path='/foo', path='bar')
        assert buildstep.path == '/foo/bar'
        assert buildstep.repo_path == '/foo'

        buildstep = self.get_buildstep(repo_path='/foo', path='/bar')
        assert buildstep.path == '/bar'
        assert buildstep.repo_path == '/foo'

        buildstep = self.get_buildstep(repo_path='foo', path=DEFAULT_PATH)
        assert buildstep.path == 'foo/./source/'
        assert buildstep.repo_path == 'foo'
