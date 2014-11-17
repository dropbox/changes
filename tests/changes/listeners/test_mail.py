import mock

from changes.config import db
from changes.constants import Result
from changes.models import ProjectOption, ItemOption
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
        build = self.create_build(project, result=Result.passed, author=author)
        job = self.create_job(build)

        handler = MailNotificationHandler()
        recipients = handler.get_recipients(job)

        assert recipients == ['{0} <foo@example.com>'.format(author.name)]

    def test_without_author_option(self):
        project = self.create_project()
        db.session.add(ProjectOption(
            project=project, name='mail.notify-author', value='0'))
        author = self.create_author('foo@example.com')
        build = self.create_build(project, result=Result.failed, author=author)
        job = self.create_job(build)
        db.session.commit()

        handler = MailNotificationHandler()
        recipients = handler.get_recipients(job)

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
        job = self.create_job(build)
        db.session.commit()

        handler = MailNotificationHandler()
        recipients = handler.get_recipients(job)

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
        job = self.create_job(build=build)
        db.session.commit()

        handler = MailNotificationHandler()
        recipients = handler.get_recipients(job)

        assert recipients == ['{0} <foo@example.com>'.format(author.name)]

        build = self.create_build(
            project=project,
            result=Result.failed,
            author=author,
        )
        job = self.create_job(build=build)

        handler = MailNotificationHandler()
        recipients = handler.get_recipients(job)

        assert recipients == [
            '{0} <foo@example.com>'.format(author.name),
            'test@example.com',
            'bar@example.com',
        ]


class SendTestCase(TestCase):
    @mock.patch.object(MailNotificationHandler, 'get_recipients')
    def test_simple(self, get_recipients):
        project = self.create_project(name='test', slug='test')
        build = self.create_build(project, target='D1234', label='Test diff')
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

        job_link = 'http://example.com/projects/test/builds/%s/jobs/%s/' % (build.id.hex, job.id.hex,)
        log_link = '%slogs/%s/' % (job_link, logsource.id.hex)

        get_recipients.return_value = ['foo@example.com', 'Bob <bob@example.com>']

        handler = MailNotificationHandler()
        handler.send(job, None)

        assert len(self.outbox) == 1
        msg = self.outbox[0]

        assert msg.subject == '%s FAILED - %s %s #%s.%s' % (
            job.build.target, job.project.name, job.build.label, job.build.number, job.number)
        assert msg.recipients == ['foo@example.com', 'Bob <bob@example.com>']
        assert msg.extra_headers['Reply-To'] == 'foo@example.com, Bob <bob@example.com>'

        assert job_link in msg.html
        assert job_link in msg.body
        assert log_link in msg.html
        assert log_link in msg.body

        assert msg.as_string()

    @mock.patch.object(MailNotificationHandler, 'get_recipients')
    def test_subject_branch(self, get_recipients):
        project = self.create_project(name='test', slug='test')
        repo = project.repository
        branches = ['master', 'branch1']
        branch_str = ' (%s)' % ','.join(branches)
        revision = self.create_revision(repository=repo, branches=branches)
        source = self.create_source(
            project=project,
            revision=revision,
        )
        build = self.create_build(
            project=project,
            source=source,
            label='Test diff',
            target='D1234',
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

        job_link = 'http://example.com/projects/test/builds/%s/jobs/%s/' % (build.id.hex, job.id.hex,)
        log_link = '%slogs/%s/' % (job_link, logsource.id.hex)

        get_recipients.return_value = ['foo@example.com', 'Bob <bob@example.com>']

        handler = MailNotificationHandler()
        handler.send(job, None)

        assert len(self.outbox) == 1
        msg = self.outbox[0]

        assert msg.subject == '%s FAILED - %s%s %s #%s.%s' % (
            job.build.target, job.project.name, branch_str, job.build.label, job.build.number, job.number)
        assert msg.recipients == ['foo@example.com', 'Bob <bob@example.com>']
        assert msg.extra_headers['Reply-To'] == 'foo@example.com, Bob <bob@example.com>'

        assert job_link in msg.html
        assert job_link in msg.body
        assert log_link in msg.html
        assert log_link in msg.body

        assert msg.as_string()

    @mock.patch.object(MailNotificationHandler, 'get_recipients')
    def test_multiple_sources(self, get_recipients):
        project = self.create_project(name='test', slug='test')
        build = self.create_build(project, target='D1234')
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

        job_link = 'http://example.com/projects/test/builds/%s/jobs/%s/' % (build.id.hex, job.id.hex,)
        log_link1 = '%slogs/%s/' % (job_link, logsource.id.hex)
        log_link2 = '%slogs/%s/' % (job_link, logsource2.id.hex)

        get_recipients.return_value = ['foo@example.com', 'Bob <bob@example.com>']

        handler = MailNotificationHandler()
        handler.send(job, None)

        assert len(self.outbox) == 1
        msg = self.outbox[0]

        assert msg.subject == '%s FAILED - %s %s #%s.%s' % (
            job.build.target, job.project.name, job.build.label, job.build.number, job.number)
        assert msg.recipients == ['foo@example.com', 'Bob <bob@example.com>']
        assert msg.extra_headers['Reply-To'] == 'foo@example.com, Bob <bob@example.com>'

        assert job_link in msg.html
        assert job_link in msg.body
        assert log_link1 in msg.html
        assert log_link1 in msg.body
        assert log_link2 in msg.html
        assert log_link2 in msg.body

        assert msg.as_string()


class GetJobOptionsTestCase(TestCase):
    def test_simple(self):
        project = self.create_project()
        plan = self.create_plan(project)
        build = self.create_build(project)
        job = self.create_job(build)

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
        assert handler.get_job_options(job) == {
            'mail.notify-addresses': 'foo@example.com',
            'mail.notify-author': '0',
        }
