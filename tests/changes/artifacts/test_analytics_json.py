from cStringIO import StringIO

import json
import mock

from flask import current_app

from changes.artifacts.analytics_json import AnalyticsJsonHandler, MAX_ENTRIES
from changes.models.failurereason import FailureReason
from changes.testutils import TestCase


class AnalyticsJsonHandlerTest(TestCase):

    def setUp(self):
        super(AnalyticsJsonHandlerTest, self).setUp()
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)
        jobphase = self.create_jobphase(job)
        self.jobstep = self.create_jobstep(jobphase)
        self.artifact = self.create_artifact(self.jobstep, 'CHANGES_ANALYTICS.json')

    def test_can_process(self):
        assert AnalyticsJsonHandler.can_process('CHANGES_ANALYTICS.json')
        assert AnalyticsJsonHandler.can_process('my_special_sort_of.CHANGES_ANALYTICS.json')
        assert not AnalyticsJsonHandler.can_process('changes_analytics.json')
        assert not AnalyticsJsonHandler.can_process('CHANGES_ANALYTICS')
        assert not AnalyticsJsonHandler.can_process('new_CHANGES_ANALYTICS.json')

    def test_not_json(self):
        handler = AnalyticsJsonHandler(self.jobstep)

        fp = StringIO("This is not valid JSON")
        handler.process(fp, self.artifact)
        failure_reason = FailureReason.query.filter(FailureReason.step_id == self.jobstep.id).first()
        assert failure_reason
        assert failure_reason.reason == 'malformed_artifact'

    def test_wrong_structure(self):
        handler = AnalyticsJsonHandler(self.jobstep)

        fp = StringIO(json.dumps([{'index': n} for n in xrange(2)]))
        handler.process(fp, self.artifact)
        failure_reason = FailureReason.query.filter(FailureReason.step_id == self.jobstep.id).first()
        assert failure_reason
        assert failure_reason.reason == 'malformed_artifact'

    def test_too_many_entries(self):
        handler = AnalyticsJsonHandler(self.jobstep)

        fp = StringIO(json.dumps({
            'table': 'a_permitted_table',
            'entries': [{'index': n} for n in xrange(MAX_ENTRIES + 1)],
        }))
        current_app.config['ANALYTICS_PROJECT_TABLES'] = ['a_permitted_table']
        current_app.config['ANALYTICS_PROJECT_POST_URL'] = 'URL'
        with mock.patch('changes.artifacts.analytics_json._post_analytics_data') as post_analytics:
            handler.process(fp, self.artifact)
            assert post_analytics.call_count == 0
        failure_reason = FailureReason.query.filter(FailureReason.step_id == self.jobstep.id).first()
        assert failure_reason
        assert failure_reason.reason == 'malformed_artifact'

    def test_valid(self):
        handler = AnalyticsJsonHandler(self.jobstep)
        fp = StringIO(json.dumps({
            'table': 'a_permitted_table',
            'entries': [{'index': n} for n in xrange(2)],
        }))

        current_app.config['ANALYTICS_PROJECT_TABLES'] = ['a_permitted_table']
        current_app.config['ANALYTICS_PROJECT_POST_URL'] = 'URL'
        expected_data = [{'index': n, 'jobstep_id': self.jobstep.id.hex} for n in xrange(2)]
        with mock.patch('changes.artifacts.analytics_json._post_analytics_data') as post_analytics:
            handler.process(fp, self.artifact)
            post_analytics.assert_called_once_with('URL', 'a_permitted_table', expected_data)

        assert not FailureReason.query.filter(FailureReason.step_id == self.jobstep.id).first()

    def test_dry_run(self):
        handler = AnalyticsJsonHandler(self.jobstep)
        fp = StringIO(json.dumps({
            'table': 'DRY_RUN:invalid_table',
            'entries': [{'index': n} for n in xrange(2)],
        }))

        current_app.config['ANALYTICS_PROJECT_TABLES'] = ['a_permitted_table']
        current_app.config['ANALYTICS_PROJECT_POST_URL'] = 'URL'
        with mock.patch('changes.artifacts.analytics_json._post_analytics_data') as post_analytics:
            handler.process(fp, self.artifact)
            assert post_analytics.call_count == 0

        assert not FailureReason.query.filter(FailureReason.step_id == self.jobstep.id).first()
