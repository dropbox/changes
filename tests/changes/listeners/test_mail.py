from datetime import datetime
from flask import current_app

import mock
import uuid

from changes.config import db
from changes.constants import Result, Status
from changes.models.option import ItemOption
from changes.models.project import ProjectOption
from changes.lib import build_context_lib
from changes.listeners.mail import filter_recipients, MailNotificationHandler, build_finished_handler
from changes.testutils.cases import TestCase


class FilterRecipientsTestCase(TestCase):
    def test_simple(self):
        results = filter_recipients(
            ['foo@example.com', 'bar@localhost'], ['example.com'])

        assert results == ['foo@example.com']

        results = filter_recipients(
            ['foo@example.com', 'bar@localhost'], ['example.com', 'localhost'])

        assert results == ['foo@example.com', 'bar@localhost']

        results = filter_recipients(
            ['Foo Bar <foo@example.com>'], ['example.com'])

        assert results == ['Foo Bar <foo@example.com>']


class GetRecipientsTestCase(TestCase):
    def test_default_options(self):
        project = self.create_project()
        author = self.create_author('foo@example.com')
        build = self.create_build(project, result=Result.failed, author=author)

        handler = MailNotificationHandler()
        recipients = handler.get_build_recipients(build)

        assert recipients == ['{0} <foo@example.com>'.format(author.name)]

    def test_without_author_option(self):
        project = self.create_project()
        db.session.add(ProjectOption(
            project=project, name='mail.notify-author', value='0'))
        author = self.create_author('foo@example.com')
        build = self.create_build(project, result=Result.failed, author=author)
        db.session.commit()

        handler = MailNotificationHandler()
        recipients = handler.get_build_recipients(build)

        assert recipients == []

    def test_with_addressees(self):
        project = self.create_project()
        db.session.add(ProjectOption(
            project=project, name='mail.notify-author', value='1'))
        db.session.add(ProjectOption(
            project=project, name='mail.notify-addresses',
            value='test@example.com, bar@example.com'))

        author = self.create_author('foo@example.com')
        build = self.create_build(project, result=Result.failed, author=author)
        db.session.commit()

        handler = MailNotificationHandler()
        recipients = handler.get_build_recipients(build)

        assert recipients == [
            '{0} <foo@example.com>'.format(author.name),
            'test@example.com',
            'bar@example.com',
        ]

    def test_with_revision_addressees(self):
        project = self.create_project()
        db.session.add(ProjectOption(
            project=project, name='mail.notify-author', value='1'))
        db.session.add(ProjectOption(
            project=project, name='mail.notify-addresses-revisions',
            value='test@example.com, bar@example.com'))

        author = self.create_author('foo@example.com')
        author_recipient = '{0} <{1}>'.format(author.name, author.email)
        patch = self.create_patch(repository=project.repository)
        source = self.create_source(project, patch=patch)

        patch_build = self.create_build(
            project=project,
            source=source,
            author=author,
            result=Result.failed,
        )
        db.session.commit()
        patch_recipients = MailNotificationHandler().get_build_recipients(patch_build)
        assert patch_recipients == [author_recipient]

        ss_build = self.create_build(
            project=project,
            result=Result.failed,
            author=author,
            tags=['test-snapshot'],
        )
        ss_recipients = MailNotificationHandler().get_build_recipients(ss_build)
        assert ss_recipients == [author_recipient]

        commit_build = self.create_build(
            project=project,
            result=Result.failed,
            author=author,
            tags=['commit'],
        )
        commit_recipients = MailNotificationHandler().get_build_recipients(commit_build)
        assert commit_recipients == [
            author_recipient,
            'test@example.com',
            'bar@example.com',
        ]


class SendTestCase(TestCase):
    @mock.patch.object(MailNotificationHandler, 'get_collection_recipients')
    def test_simple(self, get_collection_recipients):
        project = self.create_project(name='test', slug='test')
        build = self.create_build(
            project,
            label='Test diff',
            date_started=datetime.utcnow(),
            result=Result.failed,
            status=Status.finished
        )
        job = self.create_job(build=build, result=Result.failed)
        phase = self.create_jobphase(job=job)
        step = self.create_jobstep(phase=phase)
        logsource = self.create_logsource(
            step=step,
            name='console',
        )
        self.create_logchunk(
            source=logsource,
            text='hello world',
        )

        job_link = 'http://example.com/projects/%s/builds/%s/jobs/%s/' % (
            project.slug, build.id.hex, job.id.hex,)
        log_link = '%slogs/%s/' % (job_link, logsource.id.hex)

        get_collection_recipients.return_value = ['foo@example.com', 'Bob <bob@example.com>']

        build_finished_handler(build.id)

        assert len(self.outbox) == 1
        msg = self.outbox[0]

        assert msg.subject == '%s failed - %s' % (
            'D1234', job.build.label)
        assert msg.recipients == ['foo@example.com', 'Bob <bob@example.com>']
        assert msg.extra_headers['Reply-To'] == 'foo@example.com, Bob <bob@example.com>'

        assert job_link in msg.html
        assert job_link in msg.body
        assert log_link in msg.html
        assert log_link in msg.body

        assert msg.as_string()

    @mock.patch.object(MailNotificationHandler, 'get_collection_recipients')
    def test_simple_null_message(self, get_collection_recipients):
        project = self.create_project(name='test', slug='test')
        build = self.create_build(
            project,
            label='Test diff',
            date_started=datetime.utcnow(),
            result=Result.failed,
            status=Status.finished
        )
        job = self.create_job(build=build, result=Result.failed)
        test_case = self.create_test(job, message=None, result=Result.failed)
        phase = self.create_jobphase(job=job)
        step = self.create_jobstep(phase=phase)
        logsource = self.create_logsource(
            step=step,
            name='console',
        )
        self.create_logchunk(
            source=logsource,
            text='hello world',
        )

        job_link = 'http://example.com/projects/%s/builds/%s/jobs/%s/' % (
            project.slug, build.id.hex, job.id.hex,)
        log_link = '%slogs/%s/' % (job_link, logsource.id.hex)

        get_collection_recipients.return_value = ['foo@example.com', 'Bob <bob@example.com>']

        build_finished_handler(build.id)

        assert len(self.outbox) == 1
        msg = self.outbox[0]

        assert msg.subject == '%s failed - %s' % (
            'D1234', job.build.label)
        assert msg.recipients == ['foo@example.com', 'Bob <bob@example.com>']
        assert msg.extra_headers['Reply-To'] == 'foo@example.com, Bob <bob@example.com>'

        assert job_link in msg.html
        assert job_link in msg.body
        assert log_link in msg.html
        assert log_link in msg.body

        assert msg.as_string()

    @mock.patch.object(MailNotificationHandler, 'get_collection_recipients')
    def test_subject_branch(self, get_collection_recipients):
        project = self.create_project(name='test', slug='test')
        repo = project.repository
        branches = ['master', 'branch1']
        revision = self.create_revision(repository=repo, branches=branches)
        source = self.create_source(
            project=project,
            revision=revision,
        )
        build = self.create_build(
            project=project,
            source=source,
            label='Test diff',
            date_started=datetime.utcnow(),
            result=Result.failed,
            status=Status.finished
        )
        job = self.create_job(build=build, result=Result.failed)
        phase = self.create_jobphase(job=job)
        step = self.create_jobstep(phase=phase)
        logsource = self.create_logsource(
            step=step,
            name='console',
        )
        self.create_logchunk(
            source=logsource,
            text='hello world',
        )

        job_link = 'http://example.com/projects/%s/builds/%s/jobs/%s/' % (
            project.slug, build.id.hex, job.id.hex,)
        log_link = '%slogs/%s/' % (job_link, logsource.id.hex)

        get_collection_recipients.return_value = ['foo@example.com', 'Bob <bob@example.com>']

        build_finished_handler(build.id)

        assert len(self.outbox) == 1
        msg = self.outbox[0]

        assert msg.subject == '%s failed - %s' % (
            'D1234', job.build.label)
        assert msg.recipients == ['foo@example.com', 'Bob <bob@example.com>']
        assert msg.extra_headers['Reply-To'] == 'foo@example.com, Bob <bob@example.com>'

        assert job_link in msg.html
        assert job_link in msg.body
        assert log_link in msg.html
        assert log_link in msg.body

        assert msg.as_string()

    @mock.patch.object(MailNotificationHandler, 'get_collection_recipients')
    def test_multiple_sources(self, get_collection_recipients):
        project = self.create_project(name='test', slug='test')
        build = self.create_build(
            project,
            date_started=datetime.utcnow(),
            result=Result.failed,
            status=Status.finished
        )
        job = self.create_job(build=build, result=Result.failed)
        phase = self.create_jobphase(job=job)
        step = self.create_jobstep(phase=phase)
        logsource = self.create_logsource(
            step=step,
            name='console',
        )
        self.create_logchunk(
            source=logsource,
            text='hello world',
        )
        phase2 = self.create_jobphase(job=job, label='other')
        step2 = self.create_jobstep(phase=phase2)
        logsource2 = self.create_logsource(
            step=step2,
            name='other',
        )
        self.create_logchunk(
            source=logsource2,
            text='hello world',
        )

        job_link = 'http://example.com/projects/%s/builds/%s/jobs/%s/' % (
            project.slug, build.id.hex, job.id.hex,)
        log_link1 = '%slogs/%s/' % (job_link, logsource.id.hex)
        log_link2 = '%slogs/%s/' % (job_link, logsource2.id.hex)

        get_collection_recipients.return_value = ['foo@example.com', 'Bob <bob@example.com>']

        build_finished_handler(build.id)

        assert len(self.outbox) == 1
        msg = self.outbox[0]

        assert msg.subject == '%s failed - %s' % (
            'D1234', job.build.label)
        assert msg.recipients == ['foo@example.com', 'Bob <bob@example.com>']
        assert msg.extra_headers['Reply-To'] == 'foo@example.com, Bob <bob@example.com>'

        assert job_link in msg.html
        assert job_link in msg.body
        assert log_link1 in msg.html
        assert log_link1 in msg.body
        assert log_link2 in msg.html
        assert log_link2 in msg.body

        assert msg.as_string()

    @mock.patch.object(MailNotificationHandler, 'get_collection_recipients')
    def test_max_shown(self, get_collection_recipients):
        project = self.create_project(name='test', slug='test')
        build = self.create_build(
            project,
            label='Test diff',
            date_started=datetime.utcnow(),
            result=Result.failed,
            status=Status.finished
        )
        job = self.create_job(build=build, result=Result.failed)
        phase = self.create_jobphase(job=job)
        step = self.create_jobstep(phase=phase)
        max_shown = current_app.config.get('MAX_SHOWN_ITEMS_PER_BUILD_MAIL', 3)
        total_test_count = max_shown + 1
        test_cases = []
        for i in range(total_test_count):
            test_cases.append(self.create_test(
                package='test.group.ClassName',
                name='test.group.ClassName.test_foo{}'.format(i),
                job=job,
                duration=134,
                result=Result.failed,
                ))

        get_collection_recipients.return_value = ['foo@example.com', 'Bob <bob@example.com>']

        build_finished_handler(build.id)

        assert len(self.outbox) == 1
        msg = self.outbox[0]

        text_content = msg.body
        html_content = msg.html
        assert text_content
        shown_test_count = 0
        for test_case in test_cases:
            test_link = build_context_lib._get_test_case_uri(test_case)
            if test_link in text_content:
                shown_test_count += 1
        assert shown_test_count == max_shown

        assert html_content
        assert 'Showing {} out of <strong style="font-weight: bold">{}</strong>'.format(max_shown, total_test_count) in html_content
        assert 'See all failing tests (1 remaining)' in html_content
        shown_test_count = 0
        for test_case in test_cases:
            test_link = build_context_lib._get_test_case_uri(test_case)
            if test_link in html_content:
                shown_test_count += 1
        assert shown_test_count == max_shown

    @mock.patch.object(MailNotificationHandler, 'get_collection_recipients')
    def test_max_shown_multiple_builds(self, get_collection_recipients):
        collection_id = uuid.uuid4()
        project = self.create_project(name='test', slug='test')
        build = self.create_build(
            project,
            label='Test diff',
            date_started=datetime.utcnow(),
            result=Result.failed,
            status=Status.finished,
            collection_id=collection_id,
        )
        job = self.create_job(build=build, result=Result.failed)
        phase = self.create_jobphase(job=job)
        step = self.create_jobstep(phase=phase)
        max_shown = current_app.config.get('MAX_SHOWN_ITEMS_PER_BUILD_MAIL', 3)
        total_test_count = max_shown + 1
        test_cases = []
        for i in range(total_test_count):
            test_cases.append(self.create_test(
                package='test.group.ClassName',
                name='test.group.ClassName.test_foo{}'.format(i),
                job=job,
                duration=134,
                result=Result.failed,
                ))

        build2 = self.create_build(
            project,
            label='Test diff 2',
            date_started=datetime.utcnow(),
            result=Result.failed,
            status=Status.finished,
            collection_id=collection_id,
        )
        job2 = self.create_job(build=build2, result=Result.failed)
        phase2 = self.create_jobphase(job=job2)
        step2 = self.create_jobstep(phase=phase2)
        test_case2 = self.create_test(
            package='test.group.ClassName',
            name='test.group.ClassName.test_bar',
            job=job2,
            duration=134,
            result=Result.failed,
        )

        get_collection_recipients.return_value = ['foo@example.com', 'Bob <bob@example.com>']

        build_finished_handler(build.id)

        assert len(self.outbox) == 1
        msg = self.outbox[0]

        text_content = msg.body
        html_content = msg.html
        assert 'See all failing tests (1 remaining)' in text_content
        assert build_context_lib._get_test_case_uri(test_case2) in text_content
        shown_test_count = 0
        for test_case in test_cases:
            test_link = build_context_lib._get_test_case_uri(test_case)
            if test_link in text_content:
                shown_test_count += 1
        assert shown_test_count == max_shown

        assert html_content
        assert 'Showing {} out of <strong style="font-weight: bold">{}</strong>'.format(max_shown + 1, total_test_count + 1) in html_content
        assert 'See all failing tests (1 remaining)' in html_content
        assert build_context_lib._get_test_case_uri(test_case2) in html_content
        shown_test_count = 0
        for test_case in test_cases:
            test_link = build_context_lib._get_test_case_uri(test_case)
            if test_link in html_content:
                shown_test_count += 1
        assert shown_test_count == max_shown

    @mock.patch.object(MailNotificationHandler, 'get_collection_recipients')
    def test_max_shown_log(self, get_collection_recipients):
        project = self.create_project(name='test', slug='test')
        build = self.create_build(
            project,
            label='Test diff',
            date_started=datetime.utcnow(),
            result=Result.failed,
            status=Status.finished
        )
        job = self.create_job(build=build, result=Result.failed)
        phase = self.create_jobphase(job=job)
        step = self.create_jobstep(phase=phase)
        max_shown = current_app.config.get('MAX_SHOWN_ITEMS_PER_BUILD_MAIL', 3)
        total_log_count = max_shown + 1
        log_sources = []
        for i in range(total_log_count):
            log_source = self.create_logsource(
                step=step,
                name='console' + str(i),
            )
            self.create_logchunk(
                source=log_source,
                text='hello world',
            )
            log_sources.append(log_source)
        get_collection_recipients.return_value = ['foo@example.com', 'Bob <bob@example.com>']

        build_finished_handler(build.id)

        assert len(self.outbox) == 1
        msg = self.outbox[0]

        text_content = msg.body
        html_content = msg.html

        job_link = 'http://example.com/projects/%s/builds/%s/jobs/%s/' % (
            project.slug, build.id.hex, job.id.hex,)
        shown_log_count = 0
        for log_source in log_sources:
            log_link = '%slogs/%s/' % (job_link, log_source.id.hex)
            if log_link in text_content:
                shown_log_count += 1
        assert shown_log_count == max_shown

        shown_log_count = 0
        for log_source in log_sources:
            log_link = '%slogs/%s/' % (job_link, log_source.id.hex)
            if log_link in html_content:
                shown_log_count += 1
        assert shown_log_count == max_shown


class GetBuildOptionsTestCase(TestCase):
    def test_simple(self):
        project = self.create_project()
        plan = self.create_plan(project)
        build = self.create_build(project, result=Result.failed)
        job = self.create_job(build, result=Result.failed)

        db.session.add(ItemOption(
            item_id=plan.id,
            name='mail.notify-author',
            value='0',
        ))

        db.session.add(ProjectOption(
            project_id=project.id,
            name='mail.notify-author',
            value='1',
        ))

        db.session.add(ProjectOption(
            project_id=project.id,
            name='mail.notify-addresses',
            value='foo@example.com',
        ))
        db.session.flush()

        self.create_job_plan(job, plan)

        db.session.commit()

        handler = MailNotificationHandler()
        assert handler.get_build_options(build) == {
            'mail.notify-addresses': {'foo@example.com'},
            'mail.notify-addresses-revisions': set(),
            'mail.notify-author': False,
        }

    def test_multiple_jobs(self):
        project = self.create_project()
        build = self.create_build(project, result=Result.failed)
        job1 = self.create_job(build, result=Result.failed)
        job2 = self.create_job(build, result=Result.failed)
        plan1 = self.create_plan(project)
        plan2 = self.create_plan(project)

        # Plan1 options.
        db.session.add(ItemOption(
            item_id=plan1.id,
            name='mail.notify-addresses',
            value='plan1@example.com',
        ))
        db.session.add(ItemOption(
            item_id=plan1.id,
            name='mail.notify-author',
            value='0',
        ))

        # Plan2 options.
        db.session.add(ItemOption(
            item_id=plan2.id,
            name='mail.notify-addresses',
            value='plan2@example.com',
        ))
        db.session.add(ItemOption(
            item_id=plan2.id,
            name='mail.notify-author',
            value='1',
        ))

        # Project options (notify-author is set to test that plan options can
        # override it).
        db.session.add(ProjectOption(
            project_id=project.id,
            name='mail.notify-author',
            value='0',
        ))

        # Set notify addresses to verify that it is not used when all jobs
        # override it.
        db.session.add(ProjectOption(
            project_id=project.id,
            name='mail.notify-addresses',
            value='foo@example.com',
        ))
        db.session.flush()

        for job, plan in [(job1, plan1), (job2, plan2)]:
            self.create_job_plan(job, plan)

        db.session.commit()

        handler = MailNotificationHandler()
        assert handler.get_build_options(build) == {
            'mail.notify-addresses': {'plan1@example.com', 'plan2@example.com'},
            'mail.notify-addresses-revisions': set(),
            'mail.notify-author': True,
        }
