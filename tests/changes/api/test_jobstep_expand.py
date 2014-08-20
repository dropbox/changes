from __future__ import absolute_import

from mock import Mock, patch

from changes.api.jobstep_expand import EXPAND_TYPES
from changes.expanders.base import Expander
from changes.models import Command, FutureCommand, FutureJobStep, JobStep
from changes.testutils import APITestCase


class JobStepExpandTest(APITestCase):
    @patch('changes.api.jobstep_expand.JobStepExpandAPIView.get_expander')
    def test_simple(self, mock_get_expander):
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

        expander_type = EXPAND_TYPES[0]

        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase, data={
            'max_executors': 10,
        })

        path = '/api/0/jobsteps/{0}/expand/'.format(jobstep.id.hex)

        # missing params
        resp = self.client.post(path)
        assert resp.status_code == 400

        # missing data
        resp = self.client.post(path, data={'type': expander_type})
        assert resp.status_code == 400

        # missing type
        resp = self.client.post(path, data={'data': '{"foo": "bar"}'})
        assert resp.status_code == 400

        # valid params
        resp = self.client.post(path, data={
            'type': expander_type,
            'data': '{"foo": "bar"}',
        })
        assert resp.status_code == 200, resp.data

        mock_get_expander.assert_called_once_with(expander_type)
        mock_get_expander.return_value.assert_called_once_with(
            project=project,
            data={'foo': 'bar'},
        )
        dummy_expander.validate.assert_called_once_with()
        dummy_expander.expand.assert_called_once_with(max_executors=10)

        data = self.unserialize(resp)
        assert len(data) == 1

        jobstep = JobStep.query.get(data[0]['id'])
        assert jobstep.label == 'test'
        assert jobstep.data['generated'] is True

        commands = list(Command.query.filter(
            JobStep.id == jobstep.id,
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
