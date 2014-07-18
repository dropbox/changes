from __future__ import absolute_import


from changes.buildsteps.default import DefaultBuildStep
from changes.constants import Status
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
                env="PATH=/usr/test/1"
            ),
            dict(
                script='echo "hello world 2"',
                path='/usr/test/2',
                artifacts=['artifact3.txt', 'artifact4.txt'],
                env="PATH=/usr/test/2"
            ),
            ),
        )

    def test_execute(self):
        build = self.create_build(self.create_project())
        job = self.create_job(build)

        buildstep = self.get_buildstep()
        buildstep.execute(job)

        step = job.phases[0].steps[0]

        assert step.data == {
            'build_no': None,
            'item_id': job.id.hex,
            'queued': True,
            'uri': None,
        }
        assert step.status == Status.queued
