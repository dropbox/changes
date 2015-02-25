from datetime import datetime

import mock

from changes.config import db
from changes.constants import Result
from changes.models.log import LogSource, LogChunk
from changes.models.option import ItemOption
from changes.models.project import ProjectOption
from changes.listeners.mail import filter_recipients, MailNotificationHandler
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
        patch = self.create_patch(repository=project.repository)
        source = self.create_source(project, patch=patch)
        build = self.create_build(
            project=project,
            source=source,
            author=author,
            result=Result.failed,
        )
        db.session.commit()

        handler = MailNotificationHandler()
        recipients = handler.get_build_recipients(build)

        assert recipients == ['{0} <foo@example.com>'.format(author.name)]

        build = self.create_build(
            project=project,
            result=Result.failed,
            author=author,
        )

        handler = MailNotificationHandler()
        recipients = handler.get_build_recipients(build)

        assert recipients == [
            '{0} <foo@example.com>'.format(author.name),
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
            project.id.hex, build.id.hex, job.id.hex,)
        log_link = '%slogs/%s/' % (job_link, logsource.id.hex)

        get_collection_recipients.return_value = ['foo@example.com', 'Bob <bob@example.com>']

        handler = MailNotificationHandler()
        context = handler.get_collection_context([build])
        msg = handler.get_msg(context)
        handler.send(msg, build.collection_id)

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
            project.id.hex, build.id.hex, job.id.hex,)
        log_link = '%slogs/%s/' % (job_link, logsource.id.hex)

        get_collection_recipients.return_value = ['foo@example.com', 'Bob <bob@example.com>']

        handler = MailNotificationHandler()
        context = handler.get_collection_context([build])
        msg = handler.get_msg(context)
        handler.send(msg, build.collection_id)

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
            project.id.hex, build.id.hex, job.id.hex,)
        log_link1 = '%slogs/%s/' % (job_link, logsource.id.hex)
        log_link2 = '%slogs/%s/' % (job_link, logsource2.id.hex)

        get_collection_recipients.return_value = ['foo@example.com', 'Bob <bob@example.com>']

        handler = MailNotificationHandler()
        context = handler.get_collection_context([build])
        msg = handler.get_msg(context)
        handler.send(msg, build.collection_id)

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


class GetLogClippingTestCase(TestCase):
    def test_simple(self):
        project = self.create_project()
        build = self.create_build(project)
        job = self.create_job(build)

        logsource = LogSource(
            project=project,
            job=job,
            name='console',
        )
        db.session.add(logsource)

        logchunk = LogChunk(
            project=project,
            job=job,
            source=logsource,
            offset=0,
            size=11,
            text='hello\nworld\n',
        )
        db.session.add(logchunk)
        logchunk = LogChunk(
            project=project,
            job=job,
            source=logsource,
            offset=11,
            size=11,
            text='hello\nworld\n',
        )
        db.session.add(logchunk)
        db.session.commit()

        handler = MailNotificationHandler()
        result = handler.get_log_clipping(logsource, max_size=200, max_lines=3)
        assert result == "world\r\nhello\r\nworld"

        result = handler.get_log_clipping(logsource, max_size=200, max_lines=1)
        assert result == "world"

        result = handler.get_log_clipping(logsource, max_size=5, max_lines=3)
        assert result == "world"
