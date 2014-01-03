from __future__ import absolute_import

import responses

from uuid import UUID

from changes.constants import Result
from changes.backends.jenkins.factory_builder import JenkinsFactoryBuilder
from changes.models import TestCase
from .test_builder import BaseTestCase


class SyncBuildTest(BaseTestCase):
    builder_cls = JenkinsFactoryBuilder
    builder_options = {
        'base_url': 'http://jenkins.example.com',
        'job_name': 'server',
        'downstream_job_names': ['server-downstream'],
    }

    @responses.activate
    def test_does_sync_test_report(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/api/json/',
            body=self.load_fixture('fixtures/GET/job_details_success.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/testReport/api/json/',
            body='')
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/logText/progressiveHtml/?start=0',
            match_querystring=True,
            adding_headers={'X-Text-Size': '0'},
            body='')
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server-downstream/api/xml/?depth=1&xpath=/freeStyleProject/build[action/cause/upstreamProject=%22server%22%20and%20action/cause/upstreamBuild=2]/number&wrapper=a',
            body=self.load_fixture('fixtures/GET/job_list_by_upstream.xml'),
            match_querystring=True)
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server-downstream/171/testReport/api/json/',
            body=self.load_fixture('fixtures/GET/job_test_report.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server-downstream/172/testReport/api/json/',
            body='')

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
            data={
                'build_no': 2,
                'item_id': 13,
                'job_name': 'server',
                'queued': False,
            },
        )

        builder = self.get_builder()
        builder.sync_job(job)

        test_list = sorted(TestCase.query.filter_by(job=job), key=lambda x: x.duration)

        assert len(test_list) == 2
        assert test_list[0].name == 'Test'
        assert test_list[0].package == 'tests.changes.handlers.test_xunit'
        assert test_list[0].result == Result.skipped
        assert test_list[0].message == 'collection skipped'
        assert test_list[0].duration == 0

        assert test_list[1].name == 'test_simple'
        assert test_list[1].package == 'tests.changes.api.test_build_details.BuildDetailsTest'
        assert test_list[1].result == Result.passed
        assert test_list[1].message == ''
        assert test_list[1].duration == 155
