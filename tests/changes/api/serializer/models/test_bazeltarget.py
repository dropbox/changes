from datetime import datetime

from changes.api.serializer import serialize
from changes.constants import Result, Status
from changes.testutils import TestCase


class BazelTargetCrumblerTestCase(TestCase):
    def test_simple(self):
        project = self.create_project()
        build = self.create_build(project=project)
        job = self.create_job(build=build)
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase)
        target = self.create_target(job, step,
            name='target_foo',
            duration=134,
            result=Result.failed,
            status=Status.finished,
            date_created=datetime(2013, 9, 19, 22, 15, 22),
        )
        result = serialize(target)
        assert result['id'] == str(target.id.hex)
        assert result['job']['id'] == str(job.id.hex)
        assert result['step']['id'] == str(step.id.hex)
        assert result['name'] == 'target_foo'
        assert result['dateCreated'] == '2013-09-19T22:15:22'
        assert result['result']['id'] == 'failed'
        assert result['status']['id'] == 'finished'
        assert result['duration'] == 134
        assert result['resultSource']['id'] == 'from_self'

    def test_no_step(self):
        project = self.create_project()
        build = self.create_build(project=project)
        job = self.create_job(build=build)
        phase = self.create_jobphase(job)
        target = self.create_target(job,
            name='target_foo',
            duration=134,
            result=Result.failed,
            status=Status.finished,
            date_created=datetime(2013, 9, 19, 22, 15, 22),
        )
        result = serialize(target)
        assert result['id'] == str(target.id.hex)
        assert result['job']['id'] == str(job.id.hex)
        assert 'step' not in result
        assert result['name'] == 'target_foo'
        assert result['dateCreated'] == '2013-09-19T22:15:22'
        assert result['result']['id'] == 'failed'
        assert result['status']['id'] == 'finished'
        assert result['duration'] == 134

    def test_no_result_source(self):
        project = self.create_project()
        build = self.create_build(project=project)
        job = self.create_job(build=build)
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase)
        target = self.create_target(job, step,
            name='target_foo',
            duration=134,
            result=Result.failed,
            status=Status.finished,
            date_created=datetime(2013, 9, 19, 22, 15, 22),
        )
        target.result_source = None
        result = serialize(target)
        assert result['id'] == str(target.id.hex)
        assert result['job']['id'] == str(job.id.hex)
        assert result['step']['id'] == str(step.id.hex)
        assert result['name'] == 'target_foo'
        assert result['dateCreated'] == '2013-09-19T22:15:22'
        assert result['result']['id'] == 'failed'
        assert result['status']['id'] == 'finished'
        assert result['duration'] == 134
        assert result['resultSource']['id'] == 'from_self'
