from __future__ import absolute_import

import mock
import os.path
import responses
import pytest

from flask import current_app
from uuid import UUID

from changes.config import db
from changes.constants import Status, Result
from changes.models import (
    Artifact, TestCase, Patch, LogSource, LogChunk, Job, FileCoverage
)
from changes.backends.jenkins.builder import JenkinsBuilder, chunked
from changes.testutils import (
    BackendTestCase, eager_tasks, SAMPLE_DIFF, SAMPLE_XUNIT, SAMPLE_COVERAGE
)


class BaseTestCase(BackendTestCase):
    provider = 'jenkins'
    builder_cls = JenkinsBuilder
    builder_options = {
        'base_url': 'http://jenkins.example.com',
        'job_name': 'server',
    }

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
        responses.add(
            responses.POST, 'http://jenkins.example.com/job/server/build/api/json/',
            body='',
            status=201)

        responses.add(
            responses.GET, 'http://jenkins.example.com/queue/api/xml/?xpath=%2Fqueue%2Fitem%5Baction%2Fparameter%2Fname%3D%22CHANGES_BID%22+and+action%2Fparameter%2Fvalue%3D%2281d1596fd4d642f4a6bdf86c45e014e8%22%5D%2Fid',
            body=self.load_fixture('fixtures/GET/queue_item_by_job_id.xml'),
            match_querystring=True)

        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/api/xml/?depth=1&xpath=/queue/item[action/parameter/name=%22CHANGES_BID%22%20and%20action/parameter/value=%2281d1596fd4d642f4a6bdf86c45e014e8%22]/id',
            status=404,
            match_querystring=True)

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'))

        builder = self.get_builder()
        builder.create_job(job)

        step = job.phases[0].steps[0]

        assert step.data == {
            'build_no': None,
            'item_id': '13',
            'job_name': 'server',
            'queued': True,
        }

    @responses.activate
    def test_active_creation(self):
        responses.add(
            responses.POST, 'http://jenkins.example.com/job/server/build/api/json/',
            body='',
            status=201)

        responses.add(
            responses.GET, 'http://jenkins.example.com/queue/api/xml/?xpath=%2Fqueue%2Fitem%5Baction%2Fparameter%2Fname%3D%22CHANGES_BID%22+and+action%2Fparameter%2Fvalue%3D%22f9481a17aac446718d7893b6e1c6288b%22%5D%2Fid',
            status=404,
            match_querystring=True)

        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/api/xml/?xpath=%2FfreeStyleProject%2Fbuild%5Baction%2Fparameter%2Fname%3D%22CHANGES_BID%22+and+action%2Fparameter%2Fvalue%3D%22f9481a17aac446718d7893b6e1c6288b%22%5D%2Fnumber&depth=1',
            body=self.load_fixture('fixtures/GET/build_item_by_job_id.xml'),
            match_querystring=True)

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('f9481a17aac446718d7893b6e1c6288b'),
        )

        builder = self.get_builder()
        builder.create_job(job)

        step = job.phases[0].steps[0]

        assert step.data == {
            'build_no': '1',
            'item_id': None,
            'job_name': 'server',
            'queued': False,
        }

    @responses.activate
    @mock.patch.object(JenkinsBuilder, '_find_job')
    def test_patch(self, find_job):
        responses.add(
            responses.POST, 'http://jenkins.example.com/job/server/build/api/json/',
            body='',
            status=201)

        find_job.return_value = {
            'build_no': '1',
            'item_id': None,
            'job_name': 'server',
            'queued': False,
        }

        patch = Patch(
            repository=self.repo,
            project=self.project,
            parent_revision_sha='7ebd1f2d750064652ef5bbff72452cc19e1731e0',
            label='D1345',
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


class CancelJobTest(BaseTestCase):
    @mock.patch.object(JenkinsBuilder, 'cancel_step')
    def test_simple(self, cancel_step):
        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'),
        )
        phase = self.create_jobphase(job)
        step1 = self.create_jobstep(phase, data={
            'item_id': 1,
            'job_name': 'server',
        }, status=Status.queued)

        self.create_jobstep(phase, data={
            'item_id': 2,
            'job_name': 'server',
        }, status=Status.finished)

        builder = self.get_builder()
        builder.cancel_job(job)

        cancel_step.assert_called_once_with(step1)


class CancelStepTest(BaseTestCase):
    @responses.activate
    def test_queued(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/queue/cancelItem?id=13',
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
        }, status=Status.in_progress)

        builder = self.get_builder()
        builder.cancel_step(step)

        assert step.status == Status.finished
        assert step.result == Result.aborted


class SyncBuildTest(BaseTestCase):
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
            responses.GET, 'http://jenkins.example.com/job/server/2/logText/progressiveHtml/?start=0',
            match_querystring=True,
            adding_headers={'X-Text-Size': '0'},
            body='')

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
            responses.GET, 'http://jenkins.example.com/job/server/2/logText/progressiveHtml/?start=0',
            match_querystring=True,
            adding_headers={'X-Text-Size': '0'},
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
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data=job.data)

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
            responses.GET, 'http://jenkins.example.com/job/server/2/logText/progressiveHtml/?start=0',
            match_querystring=True,
            adding_headers={'X-Text-Size': '0'},
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
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data=job.data)

        builder = self.get_builder()
        builder.sync_step(step)

        assert step.data['build_no'] == 2
        assert step.status == Status.finished
        assert step.result == Result.failed
        assert step.date_finished is not None

    @responses.activate
    def test_does_sync_test_report(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/api/json/',
            body=self.load_fixture('fixtures/GET/job_details_with_test_report.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/testReport/api/json/',
            body=self.load_fixture('fixtures/GET/job_test_report.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/logText/progressiveHtml/?start=0',
            match_querystring=True,
            adding_headers={'X-Text-Size': '0'},
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
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data=job.data)

        builder = self.get_builder()
        builder.sync_step(step)

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

    @responses.activate
    def test_does_sync_log(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/api/json/',
            body=self.load_fixture('fixtures/GET/job_details_failed.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/testReport/api/json/',
            body=self.load_fixture('fixtures/GET/job_test_report.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/logText/progressiveHtml/?start=0',
            match_querystring=True,
            adding_headers={'X-Text-Size': '7'},
            body='Foo bar')

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
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data=job.data)

        builder = self.get_builder()
        builder.sync_step(step)

        source = LogSource.query.filter_by(job=job).first()
        assert source.step == step
        assert source.name == 'server #2'
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
    @mock.patch('changes.backends.jenkins.builder.sync_artifact')
    def test_does_fire_sync_artifacts(self, sync_artifact):
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/api/json/',
            body=self.load_fixture('fixtures/GET/job_details_with_artifacts.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/testReport/api/json/',
            body=self.load_fixture('fixtures/GET/job_test_report.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/logText/progressiveHtml/?start=0',
            match_querystring=True,
            adding_headers={'X-Text-Size': '0'},
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
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data=job.data)
        builder = self.get_builder()
        builder.sync_step(step)

        log_artifact = Artifact.query.filter(
            Artifact.name == 'foobar.log',
            Artifact.step == step,
        ).first()

        assert log_artifact.data == {
            "displayPath": "foobar.log",
            "fileName": "foobar.log",
            "relativePath": "artifacts/foobar.log",
        }

        sync_artifact.delay_if_needed.assert_any_call(
            artifact_id=log_artifact.id.hex,
            task_id=log_artifact.id.hex,
            parent_task_id=step.id.hex
        )

        xunit_artifact = Artifact.query.filter(
            Artifact.name == 'tests.xml',
            Artifact.step == step,
        ).first()

        assert xunit_artifact.data == {
            "displayPath": "tests.xml",
            "fileName": "tests.xml",
            "relativePath": "artifacts/tests.xml",
        }

        sync_artifact.delay_if_needed.assert_any_call(
            artifact_id=xunit_artifact.id.hex,
            task_id=xunit_artifact.id.hex,
            parent_task_id=step.id.hex
        )

    @responses.activate
    def test_sync_artifact_as_log(self):
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/artifact/artifacts/foobar.log',
            body='hello world')

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
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data=job.data)

        builder = self.get_builder()
        builder.sync_artifact(step, {
            "displayPath": "foobar.log",
            "fileName": "foobar.log",
            "relativePath": "artifacts/foobar.log"
        })

        source = LogSource.query.filter(
            LogSource.job_id == job.id,
            LogSource.name == 'foobar.log',
        ).first()
        assert source is not None
        assert source.step == step
        assert source.project == self.project

        chunks = list(LogChunk.query.filter_by(
            source=source,
        ).order_by(LogChunk.date_created.asc()))
        assert len(chunks) == 1
        assert chunks[0].job_id == job.id
        assert chunks[0].project_id == self.project.id
        assert chunks[0].offset == 0
        assert chunks[0].size == 11
        assert chunks[0].text == 'hello world'

    @responses.activate
    def test_sync_artifact_as_xunit(self):
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
            },
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data=job.data)

        builder = self.get_builder()
        builder.sync_artifact(step, {
            "displayPath": "xunit.xml",
            "fileName": "xunit.xml",
            "relativePath": "artifacts/xunit.xml"
        })

        test_list = list(TestCase.query.filter(
            TestCase.job_id == job.id
        ))

        assert len(test_list) == 2

    @responses.activate
    def test_sync_artifact_as_coverage(self):
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
            },
        )
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, data=job.data)

        builder = self.get_builder()
        builder.sync_artifact(step, {
            "displayPath": "coverage.xml",
            "fileName": "coverage.xml",
            "relativePath": "artifacts/coverage.xml"
        })

        cover_list = list(FileCoverage.query.filter(
            FileCoverage.job_id == job.id
        ))

        assert len(cover_list) == 2


class ChunkedTest(BaseTestCase):
    def test_simple(self):
        foo = 'aaa\naaa\naaa\n'

        result = list(chunked(foo, 5))
        assert len(result) == 3
        assert result[0] == 'aaa\n'
        assert result[1] == 'aaa\n'
        assert result[2] == 'aaa\n'

        result = list(chunked(foo, 8))

        assert len(result) == 2
        assert result[0] == 'aaa\naaa\n'
        assert result[1] == 'aaa\n'

        result = list(chunked(foo, 4))

        assert len(result) == 3
        assert result[0] == 'aaa\n'
        assert result[1] == 'aaa\n'
        assert result[2] == 'aaa\n'

        foo = 'a' * 10

        result = list(chunked(foo, 2))
        assert len(result) == 5
        assert all(r == 'aa' for r in result)

        foo = 'aaaa\naaaa'

        result = list(chunked(foo, 3))
        assert len(result) == 4


class JenkinsIntegrationTest(BaseTestCase):
    """
    This test should ensure a full cycle of tasks completes successfully within
    the jenkins builder space.
    """
    # it's possible for this test to infinitely hang due to continuous polling,
    # so let's ensure we set a timeout
    @pytest.mark.timeout(1)
    @mock.patch('changes.config.redis.lock', mock.MagicMock())
    @eager_tasks
    @responses.activate
    def test_full(self):
        from changes.jobs.create_job import create_job

        # TODO: move this out of this file and integrate w/ buildstep
        responses.add(
            responses.POST, 'http://jenkins.example.com/job/server/build/api/json/',
            body='',
            status=201)
        responses.add(
            responses.GET, 'http://jenkins.example.com/queue/api/xml/?xpath=%2Fqueue%2Fitem%5Baction%2Fparameter%2Fname%3D%22CHANGES_BID%22+and+action%2Fparameter%2Fvalue%3D%2281d1596fd4d642f4a6bdf86c45e014e8%22%5D%2Fid',
            body=self.load_fixture('fixtures/GET/queue_item_by_job_id.xml'),
            match_querystring=True)
        responses.add(
            responses.GET, 'http://jenkins.example.com/queue/item/13/api/json/',
            body=self.load_fixture('fixtures/GET/queue_details_building.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/api/json/',
            body=self.load_fixture('fixtures/GET/job_details_with_test_report.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/testReport/api/json/',
            body=self.load_fixture('fixtures/GET/job_test_report.json'))
        responses.add(
            responses.GET, 'http://jenkins.example.com/job/server/2/logText/progressiveHtml/?start=0',
            match_querystring=True,
            adding_headers={'X-Text-Size': '7'},
            body='Foo bar')

        build = self.create_build(self.project)
        job = self.create_job(
            build=build,
            id=UUID('81d1596fd4d642f4a6bdf86c45e014e8'))

        plan = self.create_plan()
        plan.projects.append(self.project)
        self.create_step(
            plan, order=0, implementation='changes.backends.jenkins.buildstep.JenkinsBuildStep', data={
                'job_name': 'server',
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
        }

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

        source = LogSource.query.filter_by(job=job).first()
        assert source.name == 'server #2'
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
