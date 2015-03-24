from __future__ import absolute_import

import mock

from changes.constants import Result, Status
from changes.testutils import TestCase
from changes.listeners.log_processing import job_finished_handler


class LogProcessingTest(TestCase):

    def setUp(self):
        super(LogProcessingTest, self).setUp()

    @mock.patch('changes.listeners.log_processing.categorize.categorize')
    @mock.patch('changes.listeners.log_processing._get_rules')
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

        with mock.patch('changes.listeners.log_processing._incr') as incr:
            job_finished_handler(job_id=job.id.hex)
            incr.assert_any_call("failing-log-processed")
            incr.assert_any_call("failing-log-category-tag1")
            incr.assert_any_call("failing-log-category-tag2")

        categorize_fn.assert_called_with('project-slug', fake_rules, ''.join(chunks))

    @mock.patch('changes.listeners.log_processing.categorize.categorize')
    @mock.patch('changes.listeners.log_processing._get_rules')
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

        with mock.patch('changes.listeners.log_processing._incr') as incr:
            with mock.patch('changes.listeners.log_processing.logger.warning') as warn:
                job_finished_handler(job_id=job.id.hex)
                warn.assert_any_call(mock.ANY)
                incr.assert_any_call("failing-log-uncategorized")

        categorize_fn.assert_called_with('project-slug', fake_rules, 'Some log text')
