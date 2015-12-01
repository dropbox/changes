from __future__ import absolute_import

import mock
import os.path
import responses
import pytest
import re
import time

from flask import current_app
from uuid import UUID

from changes.config import db, redis
from changes.constants import Status, Result
from changes.models import (
    Artifact, FailureReason, FileCoverage, Job, LogChunk, LogSource,
    Patch, TestCase, TestArtifact
)
from changes.backends.jenkins.builder import JenkinsBuilder, MASTER_BLACKLIST_KEY
from changes.testutils import (
    BackendTestCase, eager_tasks, SAMPLE_DIFF, SAMPLE_XUNIT, SAMPLE_COVERAGE,
    SAMPLE_XUNIT_TESTARTIFACTS
)


class BaseTestCase(BackendTestCase):
    builder_cls = JenkinsBuilder
    builder_options = {
        'master_urls': ['http://jenkins.example.com'],
        'diff_urls': ['http://jenkins-diff.example.com'],
        'job_name': 'server',
    }

    def setUp(self):
        self.project = self.create_project()
        super(BaseTestCase, self).setUp()

    def get_builder(self, **options):
        base_options = self.builder_options.copy()
        base_options.update(options)
        return self.builder_cls(app=current_app, **base_options)

    def load_fixture(self, filename):
        filepath = os.path.join(
            os.path.dirname(__file__),
            filename,
        )
        with open(filepath, 'rb') as fp:
            return fp.read()


# TODO(dcramer): these tests need to ensure we're passing the right parameters
# to jenkins
class CreateBuildTest(BaseTestCase):
    @responses.activate
    def test_queued_creation(self):
        job_id = '81d1596fd4d642f4a6bdf86c45e014e8'
        responses.add(
            responses.POST, 'http://jenkins.example.com/job/server/build',
            body='',
            status=201)

        responses.add(
            responses.GET,
            re.compile('http://jenkins\\.example\\.com/queue/api/xml/\\?xpath=%2Fqueue%2Fitem%5Baction%2Fparameter%2Fname%3D%22CHANGES_BID%22\\+and\\+action%2Fparameter%2Fvalue%3D%22.*?%22%5D%2Fid&wrapper=x'),
            body=self.load_fixture('fixtures/GET/queue_item_by_job_id.xml'))

        responses.add(
            responses.GET,
            re.compile('http://jenkins\\.example\\.com/job/server/api/xml/\\?depth=1&xpath=/queue/item\\[action/parameter/name=%22CHANGES_BID%22%20and%20action/parameter/value=%22.*?%22\\]/id'),
            status=404)

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID(job_id))

        builder = self.get_builder()
        builder.create_job(job)

        step = job.phases[0].steps[0]

        assert step.data == {
            'build_no': None,
            'item_id': '13',
            'job_name': 'server',
            'queued': True,
            'uri': None,
            'master': 'http://jenkins.example.com',
        }

    @responses.activate
    def test_active_creation(self):
        job_id = 'f9481a17aac446718d7893b6e1c6288b'
        responses.add(
            responses.POST, 'http://jenkins.example.com/job/server/build',
            body='',
            status=201)

        responses.add(
            responses.GET,
            re.compile('http://jenkins\\.example\\.com/queue/api/xml/\\?xpath=%2Fqueue%2Fitem%5Baction%2Fparameter%2Fname%3D%22CHANGES_BID%22\\+and\\+action%2Fparameter%2Fvalue%3D%22.*?%22%5D%2Fid&wrapper=x'),
            status=404)

        responses.add(
            responses.GET,
            re.compile('http://jenkins\\.example\\.com/job/server/api/xml/\\?xpath=%2FfreeStyleProject%2Fbuild%5Baction%2Fparameter%2Fname%3D%22CHANGES_BID%22\\+and\\+action%2Fparameter%2Fvalue%3D%22.*?%22%5D%2Fnumber&depth=1&wrapper=x'),
            body=self.load_fixture('fixtures/GET/build_item_by_job_id.xml'))

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID(hex=job_id),
        )

        builder = self.get_builder()
        builder.create_job(job)

        step = job.phases[0].steps[0]

        assert step.data == {
            'build_no': '1',
            'item_id': None,
            'job_name': 'server',
            'queued': False,
            'uri': None,
            'master': 'http://jenkins.example.com',
        }

    @responses.activate
    @mock.patch.object(JenkinsBuilder, '_find_job')
    def test_patch(self, find_job):
        responses.add(
            responses.POST, 'http://jenkins-diff.example.com/job/server/build',
            body='',
            status=201)

        find_job.return_value = {
            'build_no': '1',
            'item_id': None,
            'job_name': 'server',
            'queued': False,
            'master': 'http://jenkins-diff.example.com',
        }

        patch = Patch(
            repository=self.project.repository,
            parent_revision_sha='7ebd1f2d750064652ef5bbff72452cc19e1731e0',
            diff=SAMPLE_DIFF,
        )
        db.session.add(patch)

        source = self.create_source(self.project, patch=patch)
        build = self.create_build(self.project, source=source)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8')
        )

        builder = self.get_builder()
        builder.create_job(job)

    @responses.activate
    def test_multi_master(self):
        job_id = 'f9481a17aac446718d7893b6e1c6288b'
        responses.add(
            responses.GET, 'http://jenkins-2.example.com/queue/api/json/',
            body=self.load_fixture('fixtures/GET/queue_list_other_jobs.json'),
            status=200)

        responses.add(
            responses.GET, 'http://jenkins.example.com/queue/api/json/',
            body=self.load_fixture('fixtures/GET/queue_list.json'),
            status=200)

        responses.add(
            responses.POST, 'http://jenkins-2.example.com/job/server/build',
            body='',
            status=201)

        responses.add(
            responses.GET,
            re.compile('http://jenkins-2\\.example\\.com/queue/api/xml/\\?xpath=%2Fqueue%2Fitem%5Baction%2Fparameter%2Fname%3D%22CHANGES_BID%22\\+and\\+action%2Fparameter%2Fvalue%3D%22.*?%22%5D%2Fid&wrapper=x'),
            status=404)

        responses.add(
            responses.GET,
            re.compile('http://jenkins-2\\.example\\.com/job/server/api/xml/\\?xpath=%2FfreeStyleProject%2Fbuild%5Baction%2Fparameter%2Fname%3D%22CHANGES_BID%22\\+and\\+action%2Fparameter%2Fvalue%3D%22.*?%22%5D%2Fnumber&depth=1&wrapper=x'),
            body=self.load_fixture('fixtures/GET/build_item_by_job_id.xml'))

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID(hex=job_id),
        )

        builder = self.get_builder()
        builder.master_urls = [
            'http://jenkins.example.com',
            'http://jenkins-2.example.com',
        ]
        builder.create_job(job)

        step = job.phases[0].steps[0]

        assert step.data['master'] == 'http://jenkins-2.example.com'

    @responses.activate
    def test_multi_master_one_bad(self):
        job_id = 'f9481a17aac446718d7893b6e1c6288b'
        responses.add(
            responses.GET, 'http://jenkins-2.example.com/queue/api/json/',
            body=self.load_fixture('fixtures/GET/queue_list_other_jobs.json'),
            status=200)

        # This one has a failure status.
        responses.add(
            responses.GET, 'http://jenkins.example.com/queue/api/json/',
            body='',
            status=503)

        responses.add(
            responses.POST, 'http://jenkins-2.example.com/job/server/build',
            body='',
            status=201)

        responses.add(
            responses.GET,
            re.compile('http://jenkins-2\\.example\\.com/queue/api/xml/\\?xpath=%2Fqueue%2Fitem%5Baction%2Fparameter%2Fname%3D%22CHANGES_BID%22\\+and\\+action%2Fparameter%2Fvalue%3D%22.*?%22%5D%2Fid&wrapper=x'),
            status=404)

        responses.add(
            responses.GET,
            re.compile('http://jenkins-2\\.example\\.com/job/server/api/xml/\\?xpath=%2FfreeStyleProject%2Fbuild%5Baction%2Fparameter%2Fname%3D%22CHANGES_BID%22\\+and\\+action%2Fparameter%2Fvalue%3D%22.*?%22%5D%2Fnumber&depth=1&wrapper=x'),
            body=self.load_fixture('fixtures/GET/build_item_by_job_id.xml'))

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID(hex=job_id),
        )

        builder = self.get_builder()
        builder.master_urls = [
            'http://jenkins.example.com',
            'http://jenkins-2.example.com',
        ]
        builder.create_job(job)

        step = job.phases[0].steps[0]

        assert step.data['master'] == 'http://jenkins-2.example.com'

    def test_pick_master_with_blacklist(self):
        redis.sadd(MASTER_BLACKLIST_KEY, 'http://jenkins.example.com')
        builder = self.get_builder()
        builder.master_urls = [
            'http://jenkins.example.com',
            'http://jenkins-2.example.com',
        ]
        assert 'http://jenkins-2.example.com' == builder._pick_master('job1')

    @responses.activate
    def test_jobstep_replacement(self):
        job_id = 'f9481a17aac446718d7893b6e1c6288b'
        responses.add(
            responses.POST, 'http://jenkins.example.com/job/server/build',
            body='',
            status=201)

        responses.add(
            responses.GET,
            re.compile('http://jenkins\\.example\\.com/queue/api/xml/\\?xpath=%2Fqueue%2Fitem%5Baction%2Fparameter%2Fname%3D%22CHANGES_BID%22\\+and\\+action%2Fparameter%2Fvalue%3D%22.*?%22%5D%2Fid&wrapper=x'),
            status=404)

        responses.add(
            responses.GET,
            re.compile('http://jenkins\\.example\\.com/job/server/api/xml/\\?xpath=%2FfreeStyleProject%2Fbuild%5Baction%2Fparameter%2Fname%3D%22CHANGES_BID%22\\+and\\+action%2Fparameter%2Fvalue%3D%22.*?%22%5D%2Fnumber&depth=1&wrapper=x'),
            body=self.load_fixture('fixtures/GET/build_item_by_job_id.xml'))

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID(hex=job_id),
        )

        builder = self.get_builder()
        builder.create_job(job)

        failstep = job.phases[0].steps[0]
        failstep.result = Result.infra_failed
        failstep.status = Status.finished
        db.session.add(failstep)
        db.session.commit()

        replacement_step = builder.create_job(job, replaces=failstep)
        # new jobstep should still be part of same job/phase
        assert replacement_step.job == job
        assert replacement_step.phase == failstep.phase
        # make sure .steps actually includes the new jobstep
        assert len(failstep.phase.steps) == 2
        # make sure replacement id is correctly set
        assert failstep.replacement_id == replacement_step.id

        assert replacement_step.data == {
            'build_no': '1',
            'item_id': None,
            'job_name': 'server',
            'queued': False,
            'uri': None,
            'master': 'http://jenkins.example.com',
        }


class CancelStepTest(BaseTestCase):
    @responses.activate
    def test_queued(self):
        responses.add(
            responses.POST, 'http://jenkins.example.com/queue/cancelItem?id=13',
            match_querystring=True, status=302)

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data={
            'item_id': 13,
            'job_name': 'server',
            'master': 'http://jenkins.example.com',
        }, status=Status.queued)

        builder = self.get_builder()
        builder.cancel_step(step)

        assert step.result == Result.aborted
        assert step.status == Status.finished

    @responses.activate
    def test_active(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/stop/',
            body='', status=302)

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data={
            'build_no': 2,
            'job_name': 'server',
            'master': 'http://jenkins.example.com',
        }, status=Status.in_progress)

        builder = self.get_builder()
        builder.cancel_step(step)

        assert step.status == Status.finished
        assert step.result == Result.aborted

    @responses.activate
    def test_timeouts_sync_log(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/api/json/',
            body=self.load_fixture('fixtures/GET/job_details_building.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/logText/progressiveText/?start=0',
            match_querystring=True,
            adding_headers={'X-Text-Size': '7'},
            body='Foo bar')
        responses.add(
            responses.GET, 'http://jenkins.example.com/computer/server-ubuntu-10.04%20(ami-746cf244)%20(i-836023b7)/config.xml',
            body=self.load_fixture('fixtures/GET/node_config.xml'))

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
            data={
                'build_no': 2,
                'item_id': 13,
                'job_name': 'server',
                'queued': False,
                'master': 'http://jenkins.example.com',
            },
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data=job.data)

        builder = self.get_builder()

        # The job is not yet complete after this sync step so no logs yet.
        builder.sync_step(step)
        source = LogSource.query.filter_by(job=job).first()
        assert source is None

        step.data['timed_out'] = True
        builder.cancel_step(step)

        source = LogSource.query.filter_by(job=job).first()
        assert source.step == step
        assert source.name == step.label
        assert source.project == self.project
        assert source.date_created == step.date_started

        chunks = list(LogChunk.query.filter_by(
            source=source,
        ).order_by(LogChunk.date_created.asc()))
        assert len(chunks) == 1
        assert chunks[0].job_id == job.id
        assert chunks[0].project_id == self.project.id
        assert chunks[0].offset == 0
        assert chunks[0].size == 7
        assert chunks[0].text == 'Foo bar'

        assert step.data.get('log_offset') == 7


class SyncStepTest(BaseTestCase):
    @responses.activate
    def test_waiting_in_queue(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/queue/item/13/api/json/',
            body=self.load_fixture('fixtures/GET/queue_details_pending.json'))

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data={
            'build_no': None,
            'item_id': 13,
            'job_name': 'server',
            'queued': True,
            'master': 'http://jenkins.example.com',
        })

        builder = self.get_builder()
        builder.sync_step(step)

        assert step.status == Status.queued

    @responses.activate
    def test_cancelled_in_queue(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/queue/item/13/api/json/',
            body=self.load_fixture('fixtures/GET/queue_details_cancelled.json'))

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data={
            'build_no': None,
            'item_id': 13,
            'job_name': 'server',
            'queued': True,
            'master': 'http://jenkins.example.com',
        })

        builder = self.get_builder()
        builder.sync_step(step)

        assert step.status == Status.finished
        assert step.result == Result.aborted

    @responses.activate
    def test_queued_to_active(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/queue/item/13/api/json/',
            body=self.load_fixture('fixtures/GET/queue_details_building.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/api/json/',
            body=self.load_fixture('fixtures/GET/job_details_building.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/logText/progressiveText/?start=0',
            match_querystring=True,
            adding_headers={'X-Text-Size': '0'},
            body='')
        responses.add(
            responses.GET, 'http://jenkins.example.com/computer/server-ubuntu-10.04%20(ami-746cf244)%20(i-836023b7)/config.xml',
            body=self.load_fixture('fixtures/GET/node_config.xml'))

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data={
            'build_no': None,
            'item_id': 13,
            'job_name': 'server',
            'queued': True,
            'master': 'http://jenkins.example.com',
        })
        builder = self.get_builder()
        builder.sync_step(step)

        assert step.data['build_no'] == 2

    @responses.activate
    def test_success_result(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/api/json/',
            body=self.load_fixture('fixtures/GET/job_details_success.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/logText/progressiveText/?start=0',
            match_querystring=True,
            adding_headers={'X-Text-Size': '0'},
            body='')
        responses.add(
            responses.GET, 'http://jenkins.example.com/computer/server-ubuntu-10.04%20(ami-746cf244)%20(i-836023b7)/config.xml',
            body=self.load_fixture('fixtures/GET/node_config.xml'))

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data={
            'build_no': 2,
            'item_id': 13,
            'job_name': 'server',
            'queued': False,
            'master': 'http://jenkins.example.com',
        })

        builder = self.get_builder()
        builder.sync_step(step)

        assert step.data['build_no'] == 2
        assert step.status == Status.finished
        assert step.result == Result.passed
        assert step.date_finished is not None

    @responses.activate
    def test_failed_result(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/api/json/',
            body=self.load_fixture('fixtures/GET/job_details_failed.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/logText/progressiveText/?start=0',
            match_querystring=True,
            adding_headers={'X-Text-Size': '0'},
            body='')
        responses.add(
            responses.GET, 'http://jenkins.example.com/computer/server-ubuntu-10.04%20(ami-746cf244)%20(i-836023b7)/config.xml',
            body=self.load_fixture('fixtures/GET/node_config.xml'))

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
            data={
                'build_no': 2,
                'item_id': 13,
                'job_name': 'server',
                'queued': False,
                'master': 'http://jenkins.example.com',
            },
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data=job.data)

        builder = self.get_builder()
        builder.sync_step(step)

        assert step.data['build_no'] == 2
        assert step.status == Status.finished
        assert step.result == Result.failed
        assert step.date_finished is not None

    @responses.activate
    def test_missing_manifest_result(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/api/json/',
            body=self.load_fixture('fixtures/GET/job_details_missing_manifest.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/logText/progressiveText/?start=0',
            match_querystring=True,
            adding_headers={'X-Text-Size': '0'},
            body='')
        responses.add(
            responses.GET, 'http://jenkins.example.com/computer/server-ubuntu-10.04%20(ami-746cf244)%20(i-836023b7)/config.xml',
            body=self.load_fixture('fixtures/GET/node_config.xml'))

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data={
            'build_no': 2,
            'item_id': 13,
            'job_name': 'server',
            'queued': False,
            'master': 'http://jenkins.example.com',
        })

        builder = self.get_builder()
        builder.sync_step(step)

        assert FailureReason.query.filter(
            FailureReason.step_id == step.id,
            FailureReason.reason == 'missing_manifest_json'
        )

        assert step.data['build_no'] == 2
        assert step.status == Status.finished
        assert step.result == Result.infra_failed
        assert step.date_finished is not None

    @responses.activate
    @mock.patch('changes.backends.jenkins.builder.time')
    def test_result_slow_log(self, mock_time):
        mock_time.time.return_value = time.time()

        def log_text_callback(request):
            # Zoom 10 minutes into the future; this should cause the console
            # downloading code to bail
            mock_time.time.return_value += 10 * 60
            data = "log\n" * 10000
            return (200, {'X-Text-Size': str(len(data))}, data)

        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/api/json/',
            body=self.load_fixture('fixtures/GET/job_details_failed.json'))
        responses.add_callback(
            responses.GET, 'http://jenkins.example.com/job/server/2/logText/progressiveText/?start=0',
            match_querystring=True,
            callback=log_text_callback)
        responses.add(
            responses.GET, 'http://jenkins.example.com/computer/server-ubuntu-10.04%20(ami-746cf244)%20(i-836023b7)/config.xml',
            body=self.load_fixture('fixtures/GET/node_config.xml'))

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
            data={
                'build_no': 2,
                'item_id': 13,
                'job_name': 'server',
                'queued': False,
                'master': 'http://jenkins.example.com',
            },
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data=job.data)

        builder = self.get_builder()
        builder.sync_step(step)

        assert len(step.logsources) == 1
        chunks = list(LogChunk.query.filter_by(
            source=step.logsources[0],
        ).order_by(LogChunk.offset.asc()))
        assert len(chunks) == 2
        assert "TOO LONG TO DOWNLOAD" in chunks[1].text


class SyncGenericResultsTest(BaseTestCase):
    @responses.activate
    def test_does_sync_log(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/api/json/',
            body=self.load_fixture('fixtures/GET/job_details_failed.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/logText/progressiveText/?start=0',
            match_querystring=True,
            adding_headers={'X-Text-Size': '7'},
            body='Foo bar')
        responses.add(
            responses.GET, 'http://jenkins.example.com/computer/server-ubuntu-10.04%20(ami-746cf244)%20(i-836023b7)/config.xml',
            body=self.load_fixture('fixtures/GET/node_config.xml'))

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
            data={
                'build_no': 2,
                'item_id': 13,
                'job_name': 'server',
                'queued': False,
                'master': 'http://jenkins.example.com',
            },
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data=job.data)

        builder = self.get_builder()
        builder.sync_step(step)

        source = LogSource.query.filter_by(job=job).first()
        assert source.step == step
        assert source.name == step.label
        assert source.project == self.project
        assert source.date_created == step.date_started

        chunks = list(LogChunk.query.filter_by(
            source=source,
        ).order_by(LogChunk.date_created.asc()))
        assert len(chunks) == 1
        assert chunks[0].job_id == job.id
        assert chunks[0].project_id == self.project.id
        assert chunks[0].offset == 0
        assert chunks[0].size == 7
        assert chunks[0].text == 'Foo bar'

        assert step.data.get('log_offset') == 7

    @responses.activate
    def test_does_save_artifacts(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/api/json/',
            body=self.load_fixture('fixtures/GET/job_details_with_artifacts.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/logText/progressiveText/?start=0',
            match_querystring=True,
            adding_headers={'X-Text-Size': '0'},
            body='')
        responses.add(
            responses.GET, 'http://jenkins.example.com/computer/server-ubuntu-10.04%20(ami-746cf244)%20(i-836023b7)/config.xml',
            body=self.load_fixture('fixtures/GET/node_config.xml'))

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data={
            'build_no': 2,
            'item_id': 13,
            'job_name': 'server',
            'queued': False,
            'master': 'http://jenkins.example.com',
        })

        builder = self.get_builder()
        builder.sync_step(step)

        expected_artifacts_data = dict()
        expected_artifacts_data['foobar.log'] = {
            "displayPath": "foobar.log",
            "fileName": "foobar.log",
            "relativePath": "artifacts/foobar.log",
        }
        expected_artifacts_data['foo/tests.xml'] = {
            "displayPath": "tests.xml",
            "fileName": "tests.xml",
            "relativePath": "artifacts/foo/tests.xml",
        }
        expected_artifacts_data['tests.xml'] = {
            "displayPath": "tests.xml",
            "fileName": "tests.xml",
            "relativePath": "artifacts/tests.xml",
        }

        for name, data in expected_artifacts_data.iteritems():
            artifact = Artifact.query.filter(
                Artifact.name == name,
                Artifact.step == step,
            ).first()

            assert artifact.data == data


class SyncArtifactTest(BaseTestCase):
    @responses.activate
    def test_sync_artifact_xunit(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/artifact/artifacts/xunit.xml',
            body=SAMPLE_XUNIT,
            stream=True)

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
            data={
                'build_no': 2,
                'item_id': 13,
                'job_name': 'server',
                'queued': False,
                'master': 'http://jenkins.example.com',
            },
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data=job.data)
        artifact = self.create_artifact(step, name='xunit.xml', data={
            "displayPath": "xunit.xml",
            "fileName": "xunit.xml",
            "relativePath": "artifacts/xunit.xml"
        })

        builder = self.get_builder()
        builder.sync_artifact(artifact)

        test_list = list(TestCase.query.filter(
            TestCase.job_id == job.id
        ))

        assert len(test_list) == 2

    @responses.activate
    def test_sync_artifact_coverage(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/artifact/artifacts/coverage.xml',
            body=SAMPLE_COVERAGE,
            stream=True)

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
            data={
                'build_no': 2,
                'item_id': 13,
                'job_name': 'server',
                'queued': False,
                'master': 'http://jenkins.example.com',
            },
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data=job.data)

        artifact = self.create_artifact(step, name='coverage.xml', data={
            "displayPath": "coverage.xml",
            "fileName": "coverage.xml",
            "relativePath": "artifacts/coverage.xml"
        })

        builder = self.get_builder()
        builder.sync_artifact(artifact)

        cover_list = list(FileCoverage.query.filter(
            FileCoverage.job_id == job.id
        ))

        assert len(cover_list) == 2

    @responses.activate
    def test_sync_artifact_file(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/artifact/artifacts/foo.bar',
            body=SAMPLE_COVERAGE,
            stream=True)

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
            data={
                'build_no': 2,
                'item_id': 13,
                'job_name': 'server',
                'queued': False,
                'master': 'http://jenkins.example.com',
            },
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data=job.data)

        artifact = self.create_artifact(step, name='foo.bar', data={
            "displayPath": "foo.bar",
            "fileName": "foo.bar",
            "relativePath": "artifacts/foo.bar"
        })

        builder = self.get_builder()
        builder.sync_artifact(artifact)


class SyncTestArtifactsTest(BaseTestCase):
    @responses.activate
    def test_sync_testartifacts(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/artifact/artifacts/xunit.xml',
            body=SAMPLE_XUNIT_TESTARTIFACTS,
            stream=True)

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
            data={
                'build_no': 2,
                'item_id': 13,
                'job_name': 'server',
                'queued': False,
                'master': 'http://jenkins.example.com',
            },
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data=job.data)
        artifact = self.create_artifact(step, name='xunit.xml', data={
            "displayPath": "xunit.xml",
            "fileName": "xunit.xml",
            "relativePath": "artifacts/xunit.xml"
        })

        builder = self.get_builder()
        builder.sync_artifact(artifact)

        test_artifacts = list(TestArtifact.query)
        test = TestCase.query.first()

        assert len(test_artifacts) == 1

        test_artifact = test_artifacts[0]
        assert test_artifact.file.get_file().read() == "sample_content"
        assert test_artifact.name == "sample_name.txt"
        assert str(test_artifact.type) == "Text"
        assert test_artifact.test == test


class JenkinsIntegrationTest(BaseTestCase):
    """
    This test should ensure a full cycle of tasks completes successfully within
    the jenkins builder space.
    """
    # it's possible for this test to infinitely hang due to continuous polling,
    # so let's ensure we set a timeout
    @pytest.mark.timeout(5)
    @mock.patch('changes.config.redis.lock', mock.MagicMock())
    @eager_tasks
    @responses.activate
    def test_full(self):
        from changes.jobs.create_job import create_job
        job_id = '81d1596fd4d642f4a6bdf86c45e014e8'

        # TODO: move this out of this file and integrate w/ buildstep
        responses.add(
            responses.POST, 'http://jenkins.example.com/job/server/build',
            body='',
            status=201)
        responses.add(
            responses.GET,
            re.compile('http://jenkins\\.example\\.com/queue/api/xml/\\?xpath=%2Fqueue%2Fitem%5Baction%2Fparameter%2Fname%3D%22CHANGES_BID%22\\+and\\+action%2Fparameter%2Fvalue%3D%22.*?%22%5D%2Fid&wrapper=x'),
            body=self.load_fixture('fixtures/GET/queue_item_by_job_id.xml'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/queue/item/13/api/json/',
            body=self.load_fixture('fixtures/GET/queue_details_building.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/api/json/',
            body=self.load_fixture('fixtures/GET/job_details_success.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/logText/progressiveText/?start=0',
            match_querystring=True,
            adding_headers={'X-Text-Size': '7'},
            body='Foo bar')
        responses.add(
            responses.GET, 'http://jenkins.example.com/computer/server-ubuntu-10.04%20(ami-746cf244)%20(i-836023b7)/config.xml',
            body=self.load_fixture('fixtures/GET/node_config.xml'))

        artifacts_store_requests_re = re.compile(r'http://localhost:1234/buckets/.+/artifacts')
        # Simulate test type which doesn't interact with artifacts store.
        responses.add(
            responses.GET, artifacts_store_requests_re,
            body='',
            status=404)

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID(job_id))

        plan = self.create_plan(self.project)
        self.create_step(
            plan, order=0, implementation='changes.backends.jenkins.buildstep.JenkinsBuildStep', data={
                'job_name': 'server',
                'jenkins_url': 'http://jenkins.example.com',
            },
        )
        self.create_job_plan(job, plan)

        job_id = job.id.hex
        build_id = build.id.hex

        create_job.delay(
            job_id=job_id,
            task_id=job_id,
            parent_task_id=build_id,
        )

        job = Job.query.get(job_id)

        assert job.status == Status.finished
        assert job.result == Result.passed
        assert job.date_created
        assert job.date_started
        assert job.date_finished

        phase_list = job.phases

        assert len(phase_list) == 1

        assert phase_list[0].status == Status.finished
        assert phase_list[0].result == Result.passed
        assert phase_list[0].date_created
        assert phase_list[0].date_started
        assert phase_list[0].date_finished

        step_list = phase_list[0].steps

        assert len(step_list) == 1

        assert step_list[0].status == Status.finished
        assert step_list[0].result == Result.passed
        assert step_list[0].date_created
        assert step_list[0].date_started
        assert step_list[0].date_finished
        assert step_list[0].data == {
            'item_id': '13',
            'queued': False,
            'log_offset': 7,
            'job_name': 'server',
            'build_no': 2,
            'uri': 'https://jenkins.build.itc.dropbox.com/job/server/2/',
            'master': 'http://jenkins.example.com',
        }

        node = step_list[0].node
        assert node.label == 'server-ubuntu-10.04 (ami-746cf244) (i-836023b7)'
        assert [n.label for n in node.clusters] == ['server-runner']

        source = LogSource.query.filter_by(job=job).first()
        assert source.name == step_list[0].label
        assert source.step == step_list[0]
        assert source.project == self.project
        assert source.date_created == job.date_started

        chunks = list(LogChunk.query.filter_by(
            source=source,
        ).order_by(LogChunk.date_created.asc()))
        assert len(chunks) == 1
        assert chunks[0].job_id == job.id
        assert chunks[0].project_id == self.project.id
        assert chunks[0].offset == 0
        assert chunks[0].size == 7
        assert chunks[0].text == 'Foo bar'
