from datetime import datetime

from changes.api.serializer import serialize
from changes.config import db
from changes.models import Command
from changes.testutils import TestCase


class CommandCrumblerTest(TestCase):
    def test_simple(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)
        command = Command(
            label='echo 1',
            jobstep_id=jobstep.id,
            cwd='/home/foobar',
            env={'foo': 'bar'},
            script='echo 1',
            date_created=datetime(2013, 9, 19, 22, 15, 22),
            artifacts=['junit.xml'],
        )
        db.session.add(command)
        db.session.flush()

        result = serialize(command)
        assert result['id'] == command.id.hex
        assert result['dateCreated'] == '2013-09-19T22:15:22'
        assert result['cwd'] == command.cwd
        assert result['env'] == {'foo': 'bar'}
        assert result['script'] == command.script
