from changes.constants import Result, Status
from changes.models import Command
from changes.testutils import APITestCase


class CommandDetailsTest(APITestCase):
    def test_simple(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)
        command = self.create_command(jobstep)

        path = '/api/0/commands/{0}/'.format(command.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == command.id.hex


class UpdateCommandTest(APITestCase):
    def test_simple(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(
            jobphase, status=Status.queued, result=Result.unknown,
            date_started=None, date_finished=None)

        command = self.create_command(jobstep)

        path = '/api/0/commands/{0}/'.format(command.id.hex)

        resp = self.client.post(path, data={
            'status': 'in_progress'
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == command.id.hex

        command = Command.query.get(command.id)

        assert command.status == Status.in_progress
        assert command.date_started is not None
        assert command.date_finished is None

        resp = self.client.post(path, data={
            'status': 'queued'
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == command.id.hex

        command = Command.query.get(command.id)

        assert command.status == Status.queued
        assert command.date_started is None
        assert command.date_finished is None

        resp = self.client.post(path, data={
            'status': 'finished',
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == command.id.hex

        command = Command.query.get(command.id)

        assert command.status == Status.finished
        assert command.date_started is not None
        assert command.date_finished is not None
