from __future__ import absolute_import

import json
import mock
import re
import responses

from datetime import datetime, timedelta
from flask import current_app
from mock import patch

from changes.config import db
from changes.constants import Result, Status
from changes.db.types.filestorage import FileData
from changes.jobs.sync_job_step import (
    sync_job_step, is_missing_tests, has_timed_out,
    _SNAPSHOT_TIMEOUT_BONUS_MINUTES,
    _get_artifacts_to_sync,
    _sync_from_artifact_store,
    _sync_artifacts_for_jobstep,
)
from changes.models import (
    ItemOption, ItemStat, JobStep, HistoricalImmutableStep, Task, FileCoverage,
    TestCase, FailureReason, Artifact, LogSource
)
from changes.testutils import TestCase as BaseTestCase


class HasTimedOutTest(BaseTestCase):
    def test_simple(self):
        project = self.create_project()
        plan = self.create_plan(project)
        step = self.create_step(plan)

        option = ItemOption(
            item_id=step.id,
            name='build.timeout',
            value='5',
        )
        db.session.add(option)
        db.session.flush()

        build = self.create_build(project=project)
        job = self.create_job(build=build, status=Status.queued)
        jobplan = self.create_job_plan(job, plan)

        db.session.commit()

        # for use as defaults, an instant timeout and one 1k+ years in the future.
        default_always, default_never = 0, 1e9

        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase)

        assert not has_timed_out(jobstep, jobplan, default_always)

        jobstep.status = Status.allocated
        jobstep.date_created = datetime.utcnow() - timedelta(minutes=6)
        db.session.add(jobstep)
        db.session.commit()

        # No date_started, but based on config value of 5 and date_created from
        # 6 minutes ago, should time out.
        assert has_timed_out(jobstep, jobplan, default_never)

        jobstep.status = Status.in_progress
        jobstep.date_started = datetime.utcnow()
        db.session.add(jobstep)
        db.session.commit()

        # Now we have a recent date_started, shouldn't time out.
        assert not has_timed_out(jobstep, jobplan, default_always)

        # make it so the job started 6 minutes ago.
        jobstep.date_started = datetime.utcnow() - timedelta(minutes=6)
        db.session.add(jobstep)
        db.session.commit()

        # Based on config value of 5, should time out.
        assert has_timed_out(jobstep, jobplan, default_never)

        jobstep.status = Status.allocated
        db.session.add(jobstep)
        db.session.commit()

        # Doesn't require 'in_progress' to time out.
        assert has_timed_out(jobstep, jobplan, default_never)

        jobplan.data['snapshot']['steps'][0]['options'][option.name] = '0'
        db.session.add(jobplan)
        db.session.commit()

        # The timeout option is unset, so default is used.
        assert has_timed_out(jobstep, jobplan, 4)
        assert not has_timed_out(jobstep, jobplan, 7)

        # Make sure we don't ignore 0 as default like we do with the option.
        assert has_timed_out(jobstep, jobplan, 0)

        jobplan.data['snapshot']['steps'][0]['options'][option.name] = '7'
        db.session.add(jobplan)
        db.session.commit()

        assert not has_timed_out(jobstep, jobplan, default_always)

    def test_snapshot(self):
        project = self.create_project()
        plan = self.create_plan(project)
        step = self.create_step(plan)

        option = ItemOption(
            item_id=step.id,
            name='build.timeout',
            value='5',
        )
        db.session.add(option)
        db.session.flush()

        build = self.create_build(project=project)
        job = self.create_job(build=build, status=Status.in_progress)
        jobplan = self.create_job_plan(job, plan)

        db.session.commit()

        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase,
                status=Status.in_progress,
                date_started=datetime.utcnow() - timedelta(minutes=4 + _SNAPSHOT_TIMEOUT_BONUS_MINUTES))

        with patch('changes.jobs.sync_job_step._is_snapshot_job', return_value=False):
            assert has_timed_out(jobstep, jobplan, 0)

        with patch('changes.jobs.sync_job_step._is_snapshot_job', return_value=True):
            assert not has_timed_out(jobstep, jobplan, 0)


class IsMissingTestsTest(BaseTestCase):
    def test_single_phase(self):
        project = self.create_project()
        plan = self.create_plan(project)

        option = ItemOption(
            item_id=plan.id,
            name='build.expect-tests',
            value='0',
        )
        db.session.add(option)
        db.session.commit()

        build = self.create_build(project=project)
        job = self.create_job(build=build)
        jobplan = self.create_job_plan(job, plan)
        jobphase = self.create_jobphase(
            job=job,
            date_started=datetime(2013, 9, 19, 22, 15, 24),
        )
        jobstep = self.create_jobstep(jobphase)
        jobstep2 = self.create_jobstep(jobphase)

        assert not is_missing_tests(jobstep, jobplan)

        jobplan.data['snapshot']['options'][option.name] = '1'
        db.session.add(jobplan)
        db.session.commit()

        assert is_missing_tests(jobstep, jobplan)

        testcase = TestCase(
            project_id=project.id,
            job_id=job.id,
            step_id=jobstep2.id,
            name='test',
        )
        db.session.add(testcase)
        db.session.commit()

        assert is_missing_tests(jobstep, jobplan)

        testcase = TestCase(
            project_id=project.id,
            job_id=job.id,
            step_id=jobstep.id,
            name='test2',
        )
        db.session.add(testcase)
        db.session.commit()

        assert not is_missing_tests(jobstep, jobplan)

    def test_multi_phase(self):
        project = self.create_project()

        plan = self.create_plan(project)

        option = ItemOption(
            item_id=plan.id,
            name='build.expect-tests',
            value='1',
        )
        db.session.add(option)
        db.session.commit()

        build = self.create_build(project=project)
        job = self.create_job(build=build)
        jobplan = self.create_job_plan(job, plan)
        jobphase = self.create_jobphase(
            job=job,
            label='setup',
            date_created=datetime(2013, 9, 19, 22, 15, 24),
        )
        jobphase2 = self.create_jobphase(
            job=job,
            label='test',
            date_created=datetime(2013, 9, 19, 22, 16, 24),
        )
        jobstep = self.create_jobstep(jobphase)
        jobstep2 = self.create_jobstep(jobphase2)

        job2 = self.create_job(build=build)
        self.create_job_plan(job2, plan)
        # this has a later date_created than jobphase2, but shouldn't be
        # considered because it's a different job.
        self.create_jobphase(
            job=job2,
            label='differentjob',
            date_created=datetime(2013, 9, 19, 22, 17, 24),
        )

        assert not is_missing_tests(jobstep, jobplan)
        assert is_missing_tests(jobstep2, jobplan)

        testcase = TestCase(
            project_id=project.id,
            job_id=job.id,
            step_id=jobstep.id,
            name='test',
        )
        db.session.add(testcase)
        db.session.commit()

        assert not is_missing_tests(jobstep, jobplan)
        assert is_missing_tests(jobstep2, jobplan)

        testcase = TestCase(
            project_id=project.id,
            job_id=job.id,
            step_id=jobstep2.id,
            name='test2',
        )
        db.session.add(testcase)
        db.session.commit()

        assert not is_missing_tests(jobstep2, jobplan)

    def test_snapshot_build(self):
        """
        Test that a snapshot build is not missing tests, even if
        there are no test results reported from the jobstep.
        """
        project = self.create_project()
        plan = self.create_plan(project)

        option = ItemOption(
            item_id=plan.id,
            name='build.expect-tests',
            value='1',
        )
        db.session.add(option)
        db.session.commit()

        build = self.create_build(project=project)
        job = self.create_job(build=build)
        jobplan = self.create_job_plan(job, plan)
        jobphase = self.create_jobphase(
            job=job,
            date_started=datetime(2013, 9, 19, 22, 15, 24),
        )
        jobstep = self.create_jobstep(jobphase)

        assert is_missing_tests(jobstep, jobplan)
        snapshot = self.create_snapshot(project)
        snapshot_image = self.create_snapshot_image(snapshot, plan, job_id=job.id)
        assert not is_missing_tests(jobstep, jobplan)


class SyncJobStepTest(BaseTestCase):
    ARTIFACTSTORE_REQUEST_RE = re.compile(r'http://localhost:1234/buckets/.+/artifacts')

    @mock.patch('changes.config.queue.delay')
    @mock.patch.object(HistoricalImmutableStep, 'get_implementation')
    @responses.activate
    def test_in_progress(self, get_implementation, queue_delay):
        # Simulate test which doesn't interact with artifacts store.
        responses.add(responses.GET, SyncJobStepTest.ARTIFACTSTORE_REQUEST_RE, body='', status=404)

        implementation = mock.Mock()
        get_implementation.return_value = implementation

        def mark_in_progress(step):
            step.status = Status.in_progress

        project = self.create_project()
        build = self.create_build(project=project)
        job = self.create_job(build=build)

        plan = self.create_plan(project)
        self.create_step(plan, implementation='test', order=0)
        self.create_job_plan(job, plan)

        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase)
        task = self.create_task(
            parent_id=job.id,
            task_id=step.id,
            task_name='sync_job_step',
        )

        db.session.add(ItemStat(item_id=job.id, name='tests_missing', value=1))
        db.session.commit()

        implementation.update_step.side_effect = mark_in_progress

        sync_job_step(
            step_id=step.id.hex,
            task_id=step.id.hex,
            parent_task_id=job.id.hex,
        )

        implementation.update_step.assert_called_once_with(
            step=step
        )

        db.session.expire(step)
        db.session.expire(task)

        step = JobStep.query.get(step.id)

        assert step.status == Status.in_progress

        task = Task.query.get(task.id)

        assert task.status == Status.in_progress

        queue_delay.assert_any_call('sync_job_step', kwargs={
            'step_id': step.id.hex,
            'task_id': step.id.hex,
            'parent_task_id': job.id.hex,
        }, countdown=5)

    @mock.patch('changes.config.queue.delay')
    @mock.patch.object(HistoricalImmutableStep, 'get_implementation')
    @responses.activate
    def test_finished(self, get_implementation, queue_delay):
        # Simulate test type which doesn't interact with artifacts store.
        responses.add(responses.GET, SyncJobStepTest.ARTIFACTSTORE_REQUEST_RE, body='', status=404)

        implementation = mock.Mock()
        get_implementation.return_value = implementation

        def mark_finished(step):
            step.status = Status.finished
            step.result = Result.failed

        implementation.update_step.side_effect = mark_finished

        project = self.create_project()
        build = self.create_build(project=project)
        job = self.create_job(build=build)

        plan = self.create_plan(project)
        self.create_step(plan, implementation='test', order=0)
        self.create_job_plan(job, plan)

        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase)
        task = self.create_task(
            parent_id=job.id,
            task_id=step.id,
            task_name='sync_job_step',
            status=Status.finished,
        )

        db.session.add(TestCase(
            name='test',
            step_id=step.id,
            job_id=job.id,
            project_id=project.id,
            result=Result.failed,
        ))

        db.session.add(FileCoverage(
            job=job, step=step, project=job.project,
            filename='foo.py', data='CCCUUUCCCUUNNN',
            lines_covered=6,
            lines_uncovered=5,
            diff_lines_covered=3,
            diff_lines_uncovered=2,
        ))
        db.session.commit()

        sync_job_step(
            step_id=step.id.hex,
            task_id=step.id.hex,
            parent_task_id=job.id.hex,
        )

        implementation.update_step.assert_called_once_with(
            step=step
        )

        db.session.expire(step)
        db.session.expire(task)

        step = JobStep.query.get(step.id)

        assert step.status == Status.finished

        task = Task.query.get(task.id)

        assert task.status == Status.finished

        assert len(queue_delay.mock_calls) == 0

        stat = ItemStat.query.filter(
            ItemStat.item_id == step.id,
            ItemStat.name == 'tests_missing',
        ).first()
        assert stat.value == 0

        stat = ItemStat.query.filter(
            ItemStat.item_id == step.id,
            ItemStat.name == 'lines_covered',
        ).first()
        assert stat.value == 6

        stat = ItemStat.query.filter(
            ItemStat.item_id == step.id,
            ItemStat.name == 'lines_uncovered',
        ).first()
        assert stat.value == 5

        stat = ItemStat.query.filter(
            ItemStat.item_id == step.id,
            ItemStat.name == 'diff_lines_covered',
        ).first()
        assert stat.value == 3

        stat = ItemStat.query.filter(
            ItemStat.item_id == step.id,
            ItemStat.name == 'diff_lines_uncovered',
        ).first()
        assert stat.value == 2

        assert FailureReason.query.filter(
            FailureReason.step_id == step.id,
            FailureReason.reason == 'test_failures',
        )

    @mock.patch('changes.config.queue.delay')
    @mock.patch.object(HistoricalImmutableStep, 'get_implementation')
    @responses.activate
    def test_missing_test_results_and_expected(self, get_implementation, queue_delay):
        # Simulate test type which doesn't interact with artifacts store.
        responses.add(responses.GET, SyncJobStepTest.ARTIFACTSTORE_REQUEST_RE, body='', status=404)

        implementation = mock.Mock()
        get_implementation.return_value = implementation

        def mark_finished(step):
            step.status = Status.finished
            step.result = Result.passed

        implementation.update_step.side_effect = mark_finished

        project = self.create_project()
        build = self.create_build(project=project)
        job = self.create_job(build=build)

        plan = self.create_plan(project)
        self.create_step(plan, implementation='test', order=0)

        db.session.add(ItemOption(
            item_id=plan.id,
            name='build.expect-tests',
            value='1'
        ))
        db.session.commit()

        self.create_job_plan(job, plan)

        phase = self.create_jobphase(
            job=job,
            date_started=datetime(2013, 9, 19, 22, 15, 24),
        )
        step = self.create_jobstep(phase)

        with mock.patch.object(sync_job_step, 'allow_absent_from_db', True):
            sync_job_step(
                step_id=step.id.hex,
                task_id=step.id.hex,
                parent_task_id=job.id.hex,
            )

        db.session.expire(step)

        step = JobStep.query.get(step.id)

        assert step.status == Status.finished
        assert step.result == Result.failed

        stat = ItemStat.query.filter(
            ItemStat.item_id == step.id,
            ItemStat.name == 'tests_missing',
        ).first()
        assert stat.value == 1

        assert FailureReason.query.filter(
            FailureReason.step_id == step.id,
            FailureReason.reason == 'missing_tests',
        )

    @mock.patch('changes.jobs.sync_job_step.has_timed_out')
    @mock.patch.object(HistoricalImmutableStep, 'get_implementation')
    @responses.activate
    def test_timed_out(self, get_implementation, mock_has_timed_out):
        # Simulate test type which doesn't interact with artifacts store.
        responses.add(responses.GET, SyncJobStepTest.ARTIFACTSTORE_REQUEST_RE, body='', status=404)

        implementation = mock.Mock()
        get_implementation.return_value = implementation

        project = self.create_project()
        build = self.create_build(project=project)
        job = self.create_job(build=build)

        plan = self.create_plan(project)
        self.create_step(plan, implementation='test', order=0)
        jobplan = self.create_job_plan(job, plan)

        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, status=Status.in_progress)

        mock_has_timed_out.return_value = True

        current_app.config['DEFAULT_JOB_TIMEOUT_MIN'] = 99

        with mock.patch.object(sync_job_step, 'allow_absent_from_db', True):
            sync_job_step(
                step_id=step.id.hex,
                task_id=step.id.hex,
                parent_task_id=job.id.hex
            )

        mock_has_timed_out.assert_called_once_with(step, jobplan, default_timeout=99)

        implementation.cancel_step.assert_called_once_with(
            step=step,
        )

        assert step.result == Result.failed
        assert step.status == Status.finished

        assert FailureReason.query.filter(
            FailureReason.step_id == step.id,
            FailureReason.reason == 'timeout',
        )

    @mock.patch.object(HistoricalImmutableStep, 'get_implementation')
    @responses.activate
    def test_failure_reasons(self, get_implementation):
        # Simulate test type which doesn't interact with artifacts store.
        responses.add(responses.GET, SyncJobStepTest.ARTIFACTSTORE_REQUEST_RE, body='', status=404)

        implementation = mock.Mock()
        get_implementation.return_value = implementation

        project = self.create_project()
        build = self.create_build(project=project)
        job = self.create_job(build=build)

        plan = self.create_plan(project)
        self.create_step(plan, implementation='test', order=0)
        self.create_job_plan(job, plan)

        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, status=Status.finished, result=Result.passed)

        db.session.add(FailureReason(
            step_id=step.id,
            job_id=job.id,
            build_id=build.id,
            project_id=project.id,
            reason='missing_manifest_json'
        ))
        db.session.commit()

        with mock.patch.object(sync_job_step, 'allow_absent_from_db', True):
            sync_job_step(
                step_id=step.id.hex,
                task_id=step.id.hex,
                parent_task_id=job.id.hex
            )

        assert step.result == Result.infra_failed

    @mock.patch.object(Artifact, 'file')
    @responses.activate
    def test_sync_from_artifact_store(self, artifact_file):
        artifacts = [{'name': 'junit.xml', 'relativePath': 'project/junit.xml'},
                     {'name': 'console', 'relativePath': 'project/console'}]
        responses.add(responses.GET, SyncJobStepTest.ARTIFACTSTORE_REQUEST_RE, body=json.dumps(artifacts))

        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, status=Status.finished, result=Result.passed)

        _sync_from_artifact_store(step)

        logsources = LogSource.query.filter(LogSource.step_id == step.id).all()
        assert len(logsources) == 1
        assert logsources[0].name == 'console'
        assert logsources[0].in_artifact_store

        db_artifacts = Artifact.query.filter(Artifact.step_id == step.id).all()
        assert len(db_artifacts) == 1
        assert db_artifacts[0].name == 'artifactstore/project/junit.xml'
        assert artifact_file.save.call_count == 1

    def test_get_artifacts_to_sync(self):
        artifact_manager = mock.Mock()
        artifact_manager.can_process.side_effect = lambda name: not name.endswith('service.log')

        project = self.create_project()
        build = self.create_build(project=project)
        job = self.create_job(build=build)

        plan = self.create_plan(project)
        self.create_step(plan, implementation='test', order=0)
        self.create_job_plan(job, plan)

        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, status=Status.finished, result=Result.passed)

        def make_AS_file():
            return FileData({
                'filename': 'foo',
                'storage': 'changes.storage.artifactstore.ArtifactStoreFileStorage'})

        artstore_junit = self.create_artifact(step, 'artifactstore/foo/junit.xml',
                                              file=make_AS_file())
        artstore_junit2 = self.create_artifact(step, 'artifactstore/junit.xml',
                                               file=make_AS_file())
        artstore_coverage = self.create_artifact(step, 'artifactstore/coverage.xml',
                                                 file=make_AS_file())
        other_junit = self.create_artifact(step, 'bar/junit.xml')
        other_manifest = self.create_artifact(step, 'manifest.json')
        # artifact manager will say we don't process this artifact
        ignored_art = self.create_artifact(step, 'foo/service.log')
        arts = Artifact.query.filter(Artifact.step_id == step.id).all()

        assert (sorted(_get_artifacts_to_sync(arts, artifact_manager, prefer_artifactstore=True)) ==
                sorted([artstore_junit, artstore_junit2, artstore_coverage, other_manifest]))

        assert (sorted(_get_artifacts_to_sync(arts, artifact_manager, prefer_artifactstore=False)) ==
                sorted([artstore_coverage, other_junit, other_manifest]))

    @mock.patch.object(HistoricalImmutableStep, 'get_implementation')
    @mock.patch('changes.jobs.sync_job_step._get_artifacts_to_sync')
    def test_sync_artifacts_for_jobstep(self, _get_artifacts_to_sync, get_implementation):
        implementation = mock.Mock()
        get_implementation.return_value = implementation
        implementation.prefer_artifactstore.return_value = False

        project = self.create_project()
        build = self.create_build(project=project)
        job = self.create_job(build=build)

        plan = self.create_plan(project)
        self.create_step(plan, implementation='test', order=0)
        self.create_job_plan(job, plan)

        phase = self.create_jobphase(job)
        step = self.create_jobstep(phase, status=Status.finished, result=Result.passed)

        artifact = self.create_artifact(step, 'manifest.json')
        to_sync = [artifact]
        _get_artifacts_to_sync.return_value = to_sync

        _sync_artifacts_for_jobstep(step)

        assert Task.query.filter(Task.task_id == artifact.id).first()

        implementation.verify_final_artifacts.assert_called_once_with(step, to_sync)

        # verify second call is a no-op
        _sync_artifacts_for_jobstep(step)

        # not called again
        implementation.verify_final_artifacts.assert_called_once_with(step, to_sync)
