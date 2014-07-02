from __future__ import absolute_import

import mock
import responses

from uuid import UUID

from changes.backends.jenkins.factory_builder import JenkinsFactoryBuilder
from changes.models import JobPhase
from .test_builder import BaseTestCase


class SyncBuildTest(BaseTestCase):
    builder_cls = JenkinsFactoryBuilder
    builder_options = {
        'base_url': 'http://jenkins.example.com',
        'job_name': 'server',
        'downstream_job_names': ['server-downstream'],
    }

    @responses.activate
    @mock.patch('changes.config.queue.delay')
    def test_does_sync_details(self, delay):
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/api/json/',
            body=self.load_fixture('fixtures/GET/job_details_success.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/testReport/api/json/',
            body='')
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/logText/progressiveText/?start=0',
            match_querystring=True,
            adding_headers={'X-Text-Size': '0'},
            body='')
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server-downstream/api/xml/?xpath=%2FfreeStyleProject%2Fbuild%5Baction%2Fcause%2FupstreamProject%3D%22server%22+and+action%2Fcause%2FupstreamBuild%3D%222%22%5D%2Fnumber&depth=1&wrapper=a',
            body=self.load_fixture('fixtures/GET/job_list_by_upstream.xml'),
            match_querystring=True)
        responses.add(
            responses.GET, 'http://jenkins.example.com/computer/server-ubuntu-10.04%20(ami-746cf244)%20(i-836023b7)/config.xml',
            body=self.load_fixture('fixtures/GET/node_config.xml'))

        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
        )
        phase = self.create_jobphase(job, label='server')
        step = self.create_jobstep(phase, data={
            'build_no': 2,
            'item_id': 13,
            'job_name': 'server',
            'queued': False,
        })

        builder = self.get_builder()
        builder.sync_step(step)

        phase_list = list(JobPhase.query.filter(
            JobPhase.job_id == job.id,
        ).order_by(JobPhase.label.asc()))
        assert len(phase_list) == 2
        assert phase_list[0].label == 'server'
        assert phase_list[1].label == 'server-downstream'

        step_list = sorted(phase_list[1].steps, key=lambda x: x.label)
        assert len(step_list) == 2
        assert step_list[0].label == 'server-downstream #171'
        assert step_list[1].label == 'server-downstream #172'
