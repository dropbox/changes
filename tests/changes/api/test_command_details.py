from __future__ import absolute_import

from mock import Mock, patch

from changes.constants import Result, Status
from changes.expanders.base import Expander
from changes.models import (
    Command, CommandType, FutureCommand, FutureJobStep, JobStep
)
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

    @patch('changes.api.command_details.CommandDetailsAPIView.get_expander')
    def test_simple_expander(self, mock_get_expander):
        dummy_expander = Mock(spec=Expander)
        dummy_expander.expand.return_value = [FutureJobStep(
            label='test',
            commands=[FutureCommand(
                script='echo 1',
            ), FutureCommand(
                script='echo "foo"\necho "bar"',
            )],
        )]
        mock_get_expander.return_value.return_value = dummy_expander

        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase, data={
            'max_executors': 10,
        })
        command = self.create_command(
            jobstep, type=CommandType.collect_tests,
            status=Status.in_progress)

        path = '/api/0/commands/{0}/'.format(command.id.hex)

        # missing output
        resp = self.client.post(path, data={
            'status': 'finished',
        })
        assert resp.status_code == 400, resp.data

        mock_get_expander.reset_mock()

        # valid params
        resp = self.client.post(path, data={
            'status': 'finished',
            'output': '{"foo": "bar"}',
        })
        assert resp.status_code == 200, resp.data

        mock_get_expander.assert_called_once_with(command.type)
        mock_get_expander.return_value.assert_called_once_with(
            project=project,
            data={'foo': 'bar'},
        )
        dummy_expander.validate.assert_called_once_with()
        dummy_expander.expand.assert_called_once_with(max_executors=10)

        new_jobstep = JobStep.query.filter(
            JobStep.job_id == job.id,
            JobStep.id != jobstep.id,
        ).first()
        assert new_jobstep.label == 'test'
        assert new_jobstep.data['generated'] is True

        commands = list(Command.query.filter(
            Command.jobstep_id == new_jobstep.id,
        ).order_by(
            Command.order.asc(),
        ))

        assert len(commands) == 2
        assert commands[0].label == 'echo 1'
        assert commands[0].script == 'echo 1'
        assert commands[0].order == 0
        assert commands[1].label == 'echo "foo"'
        assert commands[1].script == 'echo "foo"\necho "bar"'
        assert commands[1].order == 1
