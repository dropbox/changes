from __future__ import absolute_import

from mock import Mock, patch

from changes.buildsteps.base import BuildStep
from changes.constants import Result, Status
from changes.expanders.base import Expander
from changes.models import (
    Command, CommandType, FutureCommand, FutureJobStep, JobStep, JobPhase
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

    @patch('changes.models.JobPlan.get_build_step_for_job')
    @patch('changes.api.command_details.CommandDetailsAPIView.get_expander')
    def test_simple_expander(self, mock_get_expander, mock_get_build_step_for_job):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase, data={
            'max_executors': 10,
        })
        plan = self.create_plan(project, label='test')
        self.create_step(plan)
        jobplan = self.create_job_plan(job, plan)
        command = self.create_command(
            jobstep, type=CommandType.collect_tests,
            status=Status.in_progress)

        def dummy_create_expanded_jobstep(jobstep, new_jobphase, future_jobstep):
            return future_jobstep.as_jobstep(new_jobphase)

        dummy_expander = Mock(spec=Expander)
        dummy_expander.expand.return_value = [FutureJobStep(
            label='test',
            commands=[FutureCommand(
                script='echo 1',
            ), FutureCommand(
                script='echo "foo"\necho "bar"',
            )],
        )]
        dummy_expander.default_phase_name.return_value = 'dummy'
        mock_get_expander.return_value.return_value = dummy_expander
        mock_buildstep = Mock(spec=BuildStep)
        mock_buildstep.create_expanded_jobstep.side_effect = dummy_create_expanded_jobstep

        mock_get_build_step_for_job.return_value = jobplan, mock_buildstep

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
        dummy_expander.expand.assert_called_once_with(max_executors=10,
                                                      test_stats_from=mock_buildstep.get_test_stats_from.return_value)

        phase2 = JobPhase.query.filter(
            JobPhase.job_id == job.id,
            JobPhase.id != jobphase.id,
        ).first()
        assert phase2.label == 'dummy'
        assert phase2.status == Status.queued

        new_jobstep = phase2.current_steps[0]
        assert new_jobstep.label == 'test'

    @patch('changes.models.JobPlan.get_build_step_for_job')
    @patch('changes.api.command_details.CommandDetailsAPIView.get_expander')
    def test_expander_no_commands(self, mock_get_expander, mock_get_build_step_for_job):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase, data={
            'max_executors': 10,
        })
        plan = self.create_plan(project, label='test')
        self.create_step(plan)
        jobplan = self.create_job_plan(job, plan)
        command = self.create_command(
            jobstep, type=CommandType.collect_tests,
            status=Status.in_progress)

        empty_expander = Mock(spec=Expander)
        empty_expander.expand.return_value = []
        empty_expander.default_phase_name.return_value = 'empty'
        mock_get_expander.return_value.return_value = empty_expander
        mock_buildstep = Mock(spec=BuildStep)

        mock_get_build_step_for_job.return_value = jobplan, mock_buildstep

        path = '/api/0/commands/{0}/'.format(command.id.hex)

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
        empty_expander.validate.assert_called_once_with()
        empty_expander.expand.assert_called_once_with(max_executors=10,
                                                      test_stats_from=mock_buildstep.get_test_stats_from.return_value)

        phase2 = JobPhase.query.filter(
            JobPhase.job_id == job.id,
            JobPhase.id != jobphase.id,
        ).first()
        assert phase2
        assert phase2.status == Status.finished
        assert phase2.result == Result.passed
        assert phase2.label == 'empty'

        new_steps = JobStep.query.filter(
            JobStep.phase_id == phase2.id
        )
        assert len(list(new_steps)) == 0

    @patch('changes.api.command_details.CommandDetailsAPIView.get_expander')
    def test_expander_jobstep_aborted(self, mock_get_expander):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase, data={
            'max_executors': 10,
        })
        plan = self.create_plan(project, label='test')
        self.create_step(plan)
        self.create_job_plan(job, plan)
        command = self.create_command(
            jobstep, type=CommandType.collect_tests,
            status=Status.in_progress)

        path = '/api/0/commands/{0}/'.format(command.id.hex)

        jobstep.result = Result.aborted

        resp = self.client.post(path, data={
            'status': 'finished',
            'output': '{"foo": "bar"}',
        })
        assert resp.status_code == 200, resp.data

        # jobstep was aborted, so expansion should not occur
        mock_get_expander.assert_not_called()
