from __future__ import absolute_import

from changes.buildsteps.lxc import LXCBuildStep
from changes.testutils import TestCase


class LXCBuildStepTest(TestCase):
    def get_buildstep(self):
        return LXCBuildStep(commands=(
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
        ), release='trusty')

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
            'server': 'http://example.com/api/0/',
            'jobstep_id': jobstep.id.hex,
            'release': 'trusty',
            's3-bucket': 'snapshot-bucket',
            'pre-launch': 'echo pre',
            'post-launch': 'echo post',
            'memory': '8192',
            'cpus': '4',
            'artifacts-server': 'http://localhost:1234',
        }
