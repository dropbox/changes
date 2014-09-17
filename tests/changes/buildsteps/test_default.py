from __future__ import absolute_import


from changes.buildsteps.default import (
    DEFAULT_ARTIFACTS, DEFAULT_ENV, DEFAULT_PATH, DEFAULT_RELEASE,
    DefaultBuildStep
)
from changes.config import db
from changes.constants import Status
from changes.models import Command, CommandType, FutureCommand, FutureJobStep
from changes.testutils import BackendTestCase


class DefaultBuildStepTest(BackendTestCase):
    def setUp(self):
        self.project = self.create_project()
        super(DefaultBuildStepTest, self).setUp()

    def get_buildstep(self):
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
        ))

    def test_execute(self):
        build = self.create_build(self.create_project())
        job = self.create_job(build)

        buildstep = self.get_buildstep()
        buildstep.execute(job)

        step = job.phases[0].steps[0]

        assert step.data['release'] == DEFAULT_RELEASE
        assert step.status == Status.pending_allocation

        commands = list(Command.query.filter(
            Command.jobstep_id == step.id,
        ))
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

    def test_expand_jobstep(self):
        build = self.create_build(self.create_project())
        job = self.create_job(build)
        jobphase = self.create_jobphase(job, label='foo')
        jobstep = self.create_jobstep(jobphase)

        new_jobphase = self.create_jobphase(job, label='bar')

        future_jobstep = FutureJobStep(
            label='test',
            commands=[
                FutureCommand('echo 1'),
                FutureCommand('echo "foo"\necho "bar"'),
            ],
        )

        buildstep = self.get_buildstep()
        new_jobstep = buildstep.expand_jobstep(
            jobstep, new_jobphase, future_jobstep)

        db.session.flush()

        assert new_jobstep.data['generated'] is True

        commands = list(Command.query.filter(
            Command.jobstep_id == new_jobstep.id,
        ).order_by(
            Command.order.asc(),
        ))

        assert len(commands) == 3
        assert commands[0].script == 'echo "hello world 2"'
        assert commands[0].cwd == '/usr/test/1'
        assert commands[0].type == CommandType.setup
        assert commands[0].order == 0
        assert commands[1].label == 'echo 1'
        assert commands[1].script == 'echo 1'
        assert commands[1].order == 1
        assert commands[2].label == 'echo "foo"'
        assert commands[2].script == 'echo "foo"\necho "bar"'
        assert commands[2].order == 2
