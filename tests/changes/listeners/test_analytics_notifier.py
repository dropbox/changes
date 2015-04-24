from __future__ import absolute_import

from datetime import datetime

from flask import current_app
import mock

from changes.config import db
from changes.constants import Result, Status
from changes.testutils import TestCase
from changes.models import FailureReason
from changes.listeners.analytics_notifier import (
        build_finished_handler, _get_phabricator_revision_url, _get_failure_reasons
)


def ts_to_datetime(ts):
    return datetime.utcfromtimestamp(ts)


class AnalyticsNotifierTest(TestCase):

    def setUp(self):
        super(AnalyticsNotifierTest, self).setUp()

    def _set_config_url(self, url):
        current_app.config['ANALYTICS_POST_URL'] = url

    @mock.patch('changes.listeners.analytics_notifier.post_build_data')
    def test_no_url(self, post_fn):
        self._set_config_url(None)
        project = self.create_project(name='test', slug='test')
        build = self.create_build(project, result=Result.failed)
        build_finished_handler(build_id=build.id.hex)
        self.assertEquals(post_fn.call_count, 0)

    @mock.patch('changes.listeners.analytics_notifier.post_build_data')
    def test_failed_build(self, post_fn):
        URL = "https://analytics.example.com/report?source=changes"
        self._set_config_url(URL)
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
        jobstep = self.create_jobstep(jobphase, status=Status.finished, result=Result.failed)
        db.session.add(FailureReason(step_id=jobstep.id, job_id=job.id, build_id=build.id, project_id=project.id,
                                     reason='missing_tests'))
        db.session.commit()

        with mock.patch('changes.listeners.analytics_notifier._get_phabricator_revision_url') as mock_get_phab:
            mock_get_phab.return_value = 'https://example.com/D1'
            with mock.patch('changes.listeners.analytics_notifier._get_failure_reasons') as mock_get_failures:
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
            'date_created': created,
            'date_started': started,
            'date_finished': finished,
            'phab_revision_url': 'https://example.com/D1',
            'failure_reasons': ['aborted', 'missing_tests'],
        }
        post_fn.assert_called_once_with(URL, expected_data)

    def test_get_failure_reasons_no_failures(self):
        project = self.create_project(name='test', slug='project-slug')
        build = self.create_build(project, result=Result.passed, target='D1',
                                  label='Some sweet diff')
        self.assertEquals(_get_failure_reasons(build), [])

    def test_get_failure_reasons_multiple_failures(self):
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
        db.session.commit()

        self.assertEquals(_get_failure_reasons(build),
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
