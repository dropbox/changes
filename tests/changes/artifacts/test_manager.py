from __future__ import absolute_import, print_function

from cStringIO import StringIO
from mock import Mock

from changes.artifacts.manager import Manager
from changes.testutils import TestCase


class ManagerTest(TestCase):
    def test_process_behavior(self):
        handler = Mock()

        manager = Manager()
        manager.register(handler, ['coverage.xml'])

        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)

        artifact = self.create_artifact(
            step=jobstep,
            name='junit.xml',
        )
        artifact.file.save(StringIO(), artifact.name)
        manager.process(artifact)

        assert not handler.called

        artifact = self.create_artifact(
            step=jobstep,
            name='coverage.xml',
        )
        artifact.file.save(StringIO(), artifact.name)
        manager.process(artifact)

        handler.assert_called_once_with(jobstep)
        handler.return_value.process.assert_called_once()
