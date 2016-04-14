from __future__ import absolute_import

import json

from collections import defaultdict
from datetime import datetime

from flask import current_app
import mock

from changes.config import db
from changes.constants import Result, Status
from changes.testutils import TestCase
from changes.models.failurereason import FailureReason
from changes.listeners.analytics_notifier import (
        build_finished_handler,
        job_finished_handler,
        _categorize_step_logs,
        _get_build_failure_reasons,
        _get_phabricator_revision_url,
        _get_job_failure_reasons_by_jobstep,
)


def ts_to_datetime(ts):
    return datetime.utcfromtimestamp(ts)


class AnalyticsNotifierTest(TestCase):

    def setUp(self):
        super(AnalyticsNotifierTest, self).setUp()

    def _set_config_url(self, build_url, jobstep_url=None):
        current_app.config['ANALYTICS_POST_URL'] = build_url
        current_app.config['ANALYTICS_JOBSTEP_POST_URL'] = jobstep_url

    @mock.patch('changes.listeners.analytics_notifier.post_analytics_data')
    def test_no_url(self, post_fn):
        self._set_config_url(None)
        project = self.create_project(name='test', slug='test')
        build = self.create_build(project, result=Result.failed)
        build_finished_handler(build_id=build.id.hex)
        self.assertEquals(post_fn.call_count, 0)

    @mock.patch('changes.listeners.analytics_notifier.post_analytics_data')
    def test_failed_build(self, post_fn):
        URL = "https://analytics.example.com/report?source=changes"
        self._set_config_url(URL)
        project = self.create_project(name='test', slug='project-slug')
        self.assertEquals(post_fn.call_count, 0)
        duration = 1234
        created = 1424998888
        started = created + 10
        finished = started + duration
        decided = finished + 10

        build = self.create_build(project, result=Result.failed, target='D1',
                                  label='Some sweet diff', duration=duration, tags=['commit', 'angry'],
                                  date_created=ts_to_datetime(created), date_started=ts_to_datetime(started),
                                  date_finished=ts_to_datetime(finished), date_decided=ts_to_datetime(decided))

        job = self.create_job(build=build, result=Result.failed)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase, status=Status.finished, result=Result.failed)
        self.create_jobstep(jobphase, status=Status.finished,
                            result=Result.infra_failed, replacement_id=jobstep.id)
        db.session.add(FailureReason(step_id=jobstep.id, job_id=job.id, build_id=build.id, project_id=project.id,
                                     reason='missing_tests'))
        db.session.commit()

        self.create_itemstat(item_id=build.id, name='names', value=99)
        self.create_itemstat(item_id=build.id, name='faces', value=0)

        with mock.patch('changes.listeners.analytics_notifier._get_phabricator_revision_url') as mock_get_phab:
            mock_get_phab.return_value = 'https://example.com/D1'
            with mock.patch('changes.listeners.analytics_notifier._get_build_failure_reasons') as mock_get_failures:
                mock_get_failures.return_value = ['aborted', 'missing_tests']
                build_finished_handler(build_id=build.id.hex)

        expected_data = {
            'build_id': build.id.hex,
            'number': 1,
            'target': 'D1',
            'project_slug': 'project-slug',
            'result': 'Failed',
            'label': 'Some sweet diff',
            'is_commit': True,
            'duration': 1234,
            'jobsteps_replaced': 1,
            'date_created': created,
            'date_started': started,
            'date_finished': finished,
            'date_decided': decided,
            'phab_revision_url': 'https://example.com/D1',
            'failure_reasons': ['aborted', 'missing_tests'],
            'tags': {'tags': ['angry', 'commit']},
            'tags_string': 'angry,commit',
            'item_stats': {'names': 99, 'faces': 0},
        }
        post_fn.assert_called_once_with(URL, [expected_data])

    def test_get_build_failure_reasons_no_failures(self):
        project = self.create_project(name='test', slug='project-slug')
        build = self.create_build(project, result=Result.passed, target='D1',
                                  label='Some sweet diff')
        self.assertEquals(_get_build_failure_reasons(build), [])

    def test_get_build_failure_reasons_multiple_failures(self):
        project = self.create_project(name='test', slug='project-slug')
        build = self.create_build(project, result=Result.failed, target='D1',
                                  label='Some sweet diff')
        job = self.create_job(build=build, result=Result.failed)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase, status=Status.finished, result=Result.failed)
        for reason in ('missing_tests', 'timeout', 'aborted'):
            db.session.add(FailureReason(step_id=jobstep.id, job_id=job.id, build_id=build.id, project_id=project.id,
                                         reason=reason))
        jobstep2 = self.create_jobstep(jobphase, status=Status.finished, result=Result.failed)
        for reason in ('timeout', 'insufficient_politeness'):
            db.session.add(FailureReason(step_id=jobstep2.id, job_id=job.id, build_id=build.id, project_id=project.id,
                                         reason=reason))
        jobstep3 = self.create_jobstep(jobphase, status=Status.finished, result=Result.infra_failed,
                                       replacement_id=jobstep.id)
        # shouldn't be included because jobstep3 is replaced
        db.session.add(FailureReason(step_id=jobstep3.id, job_id=job.id, build_id=build.id,
                                     project_id=project.id, reason='infra_reasons'))
        db.session.commit()

        self.assertEquals(_get_build_failure_reasons(build),
                          ['aborted', 'insufficient_politeness', 'missing_tests', 'timeout'])

    def test_get_phab_revision_url_diff(self):
        project = self.create_project(name='test', slug='test')
        source_data = {'phabricator.revisionURL': 'https://tails.corp.dropbox.com/D6789'}
        source = self.create_source(project, data=source_data)
        build = self.create_build(project, result=Result.failed, source=source, message='Some commit')
        self.assertEquals(_get_phabricator_revision_url(build), 'https://tails.corp.dropbox.com/D6789')

    def test_get_phab_revision_url_commit(self):
        project = self.create_project(name='test', slug='test')
        source_data = {}
        source = self.create_source(project, data=source_data)
        msg = """
        Some fancy commit.

        Summary: Fixes T33417.

        Test Plan: Added tests.

        Reviewers: mickey

        Reviewed By: mickey

        Subscribers: changesbot

        Maniphest Tasks: T33417

        Differential Revision: https://tails.corp.dropbox.com/D6789"""
        build = self.create_build(project, result=Result.failed, source=source, message=msg)
        self.assertEquals(_get_phabricator_revision_url(build), 'https://tails.corp.dropbox.com/D6789')

    def test_get_phab_revision_url_commit_conflict(self):
        project = self.create_project(name='test', slug='test')
        source_data = {}
        source = self.create_source(project, data=source_data)
        msg = """
        Some fancy commit.

        Summary: Fixes T33417.
          Adds messages like:
             Differential Revision: https://tails.corp.dropbox.com/D1234

        Test Plan: Added tests.

        Reviewers: mickey

        Reviewed By: mickey

        Subscribers: changesbot

        Maniphest Tasks: T33417

        Differential Revision: https://tails.corp.dropbox.com/D6789"""
        build = self.create_build(project, result=Result.failed, source=source, message=msg)
        self.assertEquals(_get_phabricator_revision_url(build), None)

    def test_get_phab_revision_url_no_message(self):
        project = self.create_project(name='test', slug='test')
        source_data = {}
        source = self.create_source(project, data=source_data)
        build = self.create_build(project, result=Result.failed, source=source, message=None)
        self.assertEquals(_get_phabricator_revision_url(build), None)

    @mock.patch('changes.listeners.analytics_notifier.categorize.categorize')
    @mock.patch('changes.listeners.analytics_notifier._get_rules')
    def test_tagged_log(self, get_rules_fn, categorize_fn):
        project = self.create_project(name='test', slug='project-slug')

        build = self.create_build(project, result=Result.failed, target='D1',
                                  label='Some sweet diff')
        job = self.create_job(build=build, result=Result.failed, status=Status.finished)
        phase = self.create_jobphase(job=job)
        step = self.create_jobstep(phase=phase)
        logsource = self.create_logsource(step=step, name='loglog')
        chunks = ['Some log text\n', 'Hey, some more log text.']
        offset = 0
        for c in chunks:
            self.create_logchunk(source=logsource, text=c, offset=offset)
            offset += len(c)

        fake_rules = object()
        get_rules_fn.return_value = fake_rules

        categorize_fn.return_value = ({"tag1", "tag2"}, {'tag1', 'tag2'})

        tags_by_step = None
        with mock.patch('changes.listeners.analytics_notifier._incr') as incr:
            tags_by_step = _categorize_step_logs(job)
            incr.assert_any_call("failing-log-processed")
            incr.assert_any_call("failing-log-category-tag1")
            incr.assert_any_call("failing-log-category-tag2")

        categorize_fn.assert_called_with('project-slug', fake_rules, ''.join(chunks))
        self.assertSetEqual(tags_by_step[step.id], {'tag1', 'tag2'})

    @mock.patch('changes.listeners.analytics_notifier.categorize.categorize')
    @mock.patch('changes.listeners.analytics_notifier._get_rules')
    def test_no_tags(self, get_rules_fn, categorize_fn):
        project = self.create_project(name='test', slug='project-slug')

        build = self.create_build(project, result=Result.failed, target='D1',
                                  label='Some sweet diff')
        job = self.create_job(build=build, result=Result.failed, status=Status.finished)
        phase = self.create_jobphase(job=job)
        step = self.create_jobstep(phase=phase)
        logsource = self.create_logsource(step=step, name='loglog')
        self.create_logchunk(source=logsource, text='Some log text')

        fake_rules = object()
        get_rules_fn.return_value = fake_rules

        # one tag was applicable, but none matched.
        categorize_fn.return_value = (set(), {'tag1'})

        tags_by_step = None
        with mock.patch('changes.listeners.analytics_notifier._incr') as incr:
            with mock.patch('changes.listeners.analytics_notifier.logger.warning') as warn:
                tags_by_step = _categorize_step_logs(job)
                warn.assert_any_call(mock.ANY, extra=mock.ANY)
                incr.assert_any_call("failing-log-uncategorized")

        categorize_fn.assert_called_with('project-slug', fake_rules, 'Some log text')
        self.assertSetEqual(tags_by_step[step.id], set())

    def test_get_job_failure_reasons_by_jobstep_passed(self):
        project = self.create_project(name='test', slug='project-slug')
        build = self.create_build(project, result=Result.passed, target='D1',
                                  label='Some sweet diff')
        job = self.create_job(build=build, result=Result.passed)
        jobphase = self.create_jobphase(job)
        jobstep = self.create_jobstep(jobphase, status=Status.finished, result=Result.passed)
        self.assertEquals(_get_job_failure_reasons_by_jobstep(job)[jobstep.id], [])

    def test_get_job_failure_reasons_by_jobstep_failures(self):
        project = self.create_project(name='test', slug='project-slug')

        build = self.create_build(project, result=Result.failed, target='D1', label='Some sweet diff')
        job = self.create_job(build=build, result=Result.failed)
        jobphase = self.create_jobphase(job)
        jobstep_a = self.create_jobstep(jobphase, status=Status.finished, result=Result.failed, label='Step A')
        jobstep_b = self.create_jobstep(jobphase, status=Status.finished, result=Result.failed, label='Step B')

        db.session.add(FailureReason(step_id=jobstep_a.id, job_id=job.id, build_id=build.id, project_id=project.id,
                                     reason='missing_tests'))
        db.session.add(FailureReason(step_id=jobstep_a.id, job_id=job.id, build_id=build.id, project_id=project.id,
                                     reason='aborted'))
        db.session.add(FailureReason(step_id=jobstep_b.id, job_id=job.id, build_id=build.id, project_id=project.id,
                                     reason='aborted'))
        db.session.commit()

        expected_data = defaultdict(list)
        expected_data[jobstep_a.id] = ['aborted', 'missing_tests']
        expected_data[jobstep_b.id] = ['aborted']
        self.assertEquals(_get_job_failure_reasons_by_jobstep(job), expected_data)

    @mock.patch('changes.listeners.analytics_notifier.post_analytics_data')
    def test_failed_job(self, post_fn):
        URL = "https://analytics.example.com/report?source=changes_jobstep"
        self._set_config_url(build_url=None, jobstep_url=URL)
        project = self.create_project(name='test', slug='project-slug')
        self.assertEquals(post_fn.call_count, 0)
        duration = 1234
        created = 1424998888
        started = created + 10
        finished = started + duration

        build = self.create_build(project, result=Result.failed, target='D1',
                                  label='Some sweet diff', duration=duration,
                                  date_created=ts_to_datetime(created), date_started=ts_to_datetime(started),
                                  date_finished=ts_to_datetime(finished))
        job = self.create_job(build=build, result=Result.failed)
        jobphase = self.create_jobphase(job)
        node = self.create_node()
        jobstep = self.create_jobstep(jobphase, status=Status.finished, result=Result.failed,
                                      label='Step 1',
                                      date_created=ts_to_datetime(created),
                                      date_started=ts_to_datetime(started),
                                      date_finished=ts_to_datetime(finished),
                                      node_id=node.id,
                                      cluster='luck')
        db.session.add(FailureReason(step_id=jobstep.id, job_id=job.id, build_id=build.id, project_id=project.id,
                                     reason='missing_tests'))
        db.session.add(FailureReason(step_id=jobstep.id, job_id=job.id, build_id=build.id, project_id=project.id,
                                     reason='aborted'))
        db.session.commit()

        with mock.patch('changes.listeners.analytics_notifier._get_job_failure_reasons_by_jobstep') as mock_get_failures:
            mock_get_failures.return_value = defaultdict(list)
            mock_get_failures.return_value[jobstep.id] = ['aborted', 'missing_tests']
            job_finished_handler(job_id=job.id.hex)

        expected_data = {
            'jobstep_id': jobstep.id.hex,
            'phase_id': jobphase.id.hex,
            'build_id': build.id.hex,
            'job_id': job.id.hex,
            'result': 'Failed',
            'replacement_id': None,
            'label': 'Step 1',
            'data': {},
            'date_created': created,
            'date_started': started,
            'date_finished': finished,
            'failure_reasons': ['aborted', 'missing_tests'],
            'log_categories': [],
            'cluster': 'luck',
            'item_stats': {},
        }
        post_fn.assert_called_once_with(URL, [expected_data])
        json.dumps(post_fn.call_args[0][1])

    @mock.patch('changes.listeners.analytics_notifier.post_analytics_data')
    def test_success_job(self, post_fn):
        URL = "https://analytics.example.com/report?source=changes_jobstep"
        self._set_config_url(build_url=None, jobstep_url=URL)
        project = self.create_project(name='test', slug='project-slug')
        self.assertEquals(post_fn.call_count, 0)
        duration = 1234
        created = 1424998888
        started = created + 10
        finished = started + duration

        build = self.create_build(project, result=Result.passed, target='D1',
                                  label='Some sweet diff', duration=duration,
                                  date_created=ts_to_datetime(created), date_started=ts_to_datetime(started),
                                  date_finished=ts_to_datetime(finished))
        job = self.create_job(build=build, result=Result.failed)
        jobphase = self.create_jobphase(job)
        node = self.create_node()
        jobstep = self.create_jobstep(jobphase, status=Status.finished, result=Result.passed,
                                      label='Step 1',
                                      date_created=ts_to_datetime(created),
                                      date_started=ts_to_datetime(started),
                                      date_finished=ts_to_datetime(finished),
                                      node_id=node.id,
                                      cluster='funk',
                                      data={'foo': 'bar'})
        self.create_itemstat(item_id=jobstep.id, name='files', value=55)
        self.create_itemstat(item_id=jobstep.id, name='lines', value=44)

        with mock.patch('changes.listeners.analytics_notifier._get_job_failure_reasons_by_jobstep') as mock_get_failures:
            mock_get_failures.return_value = defaultdict(list)
            job_finished_handler(job_id=job.id.hex)

        expected_data = {
            'jobstep_id': jobstep.id.hex,
            'phase_id': jobphase.id.hex,
            'build_id': build.id.hex,
            'job_id': job.id.hex,
            'result': 'Passed',
            'replacement_id': None,
            'label': 'Step 1',
            'data': {'foo': 'bar'},
            'date_created': created,
            'date_started': started,
            'date_finished': finished,
            'failure_reasons': [],
            'log_categories': [],
            'cluster': 'funk',
            'item_stats': {'files': 55, 'lines': 44},
        }
        post_fn.assert_called_once_with(URL, [expected_data])
        json.dumps(post_fn.call_args[0][1])
