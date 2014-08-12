from __future__ import absolute_import


from changes.buildsteps.default import (
    DEFAULT_ARTIFACTS, DEFAULT_PATH, DEFAULT_RELEASE, DefaultBuildStep
)
from changes.constants import Status
from changes.models import Command
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
        assert tuple(commands[0].artifacts) == ('artifact1.txt', 'artifact2.txt')
        assert commands[0].env == {'PATH': '/usr/test/1'}
        assert commands[1].script == 'echo "hello world 1"'
        assert commands[1].cwd == DEFAULT_PATH
        assert tuple(commands[1].artifacts) == tuple(DEFAULT_ARTIFACTS)
        assert commands[1].env == {}
