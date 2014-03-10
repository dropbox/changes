import mock

from changes.config import db
from changes.constants import Result
from changes.models import (
    ProjectOption, Patch, LogSource, LogChunk, ItemOption
)
from changes.listeners.mail import (
    job_finished_handler, send_notification, get_log_clipping, get_job_options
)
from changes.testutils.cases import TestCase


class BuildHandlerTestCase(TestCase):
    @mock.patch('changes.listeners.mail.send_notification')
    def test_default_options(self, send_notifications):
        author = self.create_author('foo@example.com')
        build = self.create_build(self.project, result=Result.passed, author=author)
        job = self.create_job(build)

        job_finished_handler(job)

        # not failing
        assert not send_notifications.called

        build = self.create_build(self.project, result=Result.failed, author=author)
        job = self.create_job(build)

        job_finished_handler(job)

        # notify author
        send_notifications.assert_called_once_with(
            job, ['Test Case <foo@example.com>']
        )

    @mock.patch('changes.listeners.mail.send_notification')
    def test_without_author_option(self, send_notifications):
        db.session.add(ProjectOption(
            project=self.project, name='mail.notify-author', value='0'))
        author = self.create_author('foo@example.com')
        build = self.create_build(self.project, result=Result.failed, author=author)
        job = self.create_job(build)

        job_finished_handler(job)

        assert not send_notifications.called

    @mock.patch('changes.listeners.mail.send_notification')
    def test_with_addressees(self, send_notifications):
        db.session.add(ProjectOption(
            project=self.project, name='mail.notify-author', value='1'))
        db.session.add(ProjectOption(
            project=self.project, name='mail.notify-addresses',
            value='test@example.com, bar@example.com'))

        author = self.create_author('foo@example.com')
        build = self.create_build(self.project, result=Result.failed, author=author)
        job = self.create_job(build)

        job_finished_handler(job)

        send_notifications.assert_called_once_with(
            job, ['Test Case <foo@example.com>', 'test@example.com', 'bar@example.com']
        )

    @mock.patch('changes.listeners.mail.send_notification')
    def test_with_revision_addressees(self, send_notifications):
        db.session.add(ProjectOption(
            project=self.project, name='mail.notify-author', value='1'))
        db.session.add(ProjectOption(
            project=self.project, name='mail.notify-addresses-revisions',
            value='test@example.com, bar@example.com'))

        author = self.create_author('foo@example.com')
        patch = Patch(
            repository=self.repo, project=self.project, label='foo',
            diff='',
        )
        source = self.create_source(self.project, patch=patch)
        build = self.create_build(
            project=self.project,
            source=source,
            author=author,
            result=Result.failed,
        )
        job = self.create_job(build=build)

        job_finished_handler(job)

        send_notifications.assert_called_once_with(
            job, ['Test Case <foo@example.com>']
        )

        send_notifications.reset_mock()

        build = self.create_build(
            project=self.project,
            result=Result.failed,
            author=author,
        )
        job = self.create_job(build=build)

        job_finished_handler(job)

        send_notifications.assert_called_once_with(
            job, ['Test Case <foo@example.com>', 'test@example.com', 'bar@example.com']
        )


class SendNotificationTestCase(TestCase):
    def test_simple(self):
        build = self.create_build(self.project)
        job = self.create_job(build=build, result=Result.failed)
        logsource = LogSource(
            project=self.project,
            job=job,
            name='console',
        )
        db.session.add(logsource)

        logchunk = LogChunk(
            project=self.project,
            job=job,
            source=logsource,
            offset=0,
            size=11,
            text='hello world',
        )
        db.session.add(logchunk)

        job_link = 'http://example.com/builds/%s/jobs/%s/' % (build.id.hex, job.id.hex,)
        log_link = '%slogs/%s/' % (job_link, logsource.id.hex)

        send_notification(job, recipients=['foo@example.com', 'Bob <bob@example.com>'])

        assert len(self.outbox) == 1
        msg = self.outbox[0]

        assert msg.subject == 'Build Failed - %s #%s.%s (%s)' % (
            job.project.name, job.build.number, job.number, job.build.source.revision_sha)
        assert msg.recipients == ['foo@example.com', 'Bob <bob@example.com>']
        assert msg.extra_headers['Reply-To'] == 'foo@example.com, Bob <bob@example.com>'
        print msg.body

        assert job_link in msg.html
        assert job_link in msg.body
        assert log_link in msg.html
        assert log_link in msg.body

        assert msg.as_string()


class GetLogClippingTestCase(TestCase):
    def test_simple(self):
        build = self.create_build(self.project)
        job = self.create_job(build)

        logsource = LogSource(
            project=self.project,
            job=job,
            name='console',
        )
        db.session.add(logsource)

        logchunk = LogChunk(
            project=self.project,
            job=job,
            source=logsource,
            offset=0,
            size=11,
            text='hello\nworld\n',
        )
        db.session.add(logchunk)
        logchunk = LogChunk(
            project=self.project,
            job=job,
            source=logsource,
            offset=11,
            size=11,
            text='hello\nworld\n',
        )
        db.session.add(logchunk)

        result = get_log_clipping(logsource, max_size=200, max_lines=3)
        assert result == "world\r\nhello\r\nworld"

        result = get_log_clipping(logsource, max_size=200, max_lines=1)
        assert result == "world"

        result = get_log_clipping(logsource, max_size=5, max_lines=3)
        assert result == "world"


class GetJobOptionsTestCase(TestCase):
    def test_simple(self):
        project = self.project
        plan = self.create_plan()
        plan.projects.append(project)
        build = self.create_build(project)
        job = self.create_job(build)
        self.create_job_plan(job, plan)

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

        assert get_job_options(job) == {
            'mail.notify-addresses': 'foo@example.com',
            'mail.notify-author': '0',
        }
