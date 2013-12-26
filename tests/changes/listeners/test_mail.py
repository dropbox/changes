import mock

from changes.config import db
from changes.constants import Result
from changes.models import ProjectOption, Patch, LogSource, LogChunk
from changes.listeners.mail import (
    build_finished_handler, send_notification, get_log_clipping
)
from changes.testutils.cases import TestCase


class BuildHandlerTestCase(TestCase):
    @mock.patch('changes.listeners.mail.send_notification')
    def test_default_options(self, send_notifications):
        author = self.create_author('foo@example.com')
        build = self.create_build(self.project, result=Result.passed, author=author)

        build_finished_handler(build)

        # not failing
        assert not send_notifications.called

        build = self.create_build(self.project, result=Result.failed, author=author)

        build_finished_handler(build)

        # notify author
        send_notifications.assert_called_once_with(
            build, ['Test Case <foo@example.com>']
        )

    @mock.patch('changes.listeners.mail.send_notification')
    def test_without_author_option(self, send_notifications):
        db.session.add(ProjectOption(
            project=self.project, name='mail.notify-author', value='0'))
        author = self.create_author('foo@example.com')
        build = self.create_build(self.project, result=Result.failed, author=author)

        build_finished_handler(build)

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

        build_finished_handler(build)

        send_notifications.assert_called_once_with(
            build, ['Test Case <foo@example.com>', 'test@example.com', 'bar@example.com']
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
        build = self.create_build(
            self.project, result=Result.failed, author=author, patch=patch)

        build_finished_handler(build)

        send_notifications.assert_called_once_with(
            build, ['Test Case <foo@example.com>']
        )

        send_notifications.reset_mock()

        build = self.create_build(
            self.project, result=Result.failed, author=author)

        build_finished_handler(build)

        send_notifications.assert_called_once_with(
            build, ['Test Case <foo@example.com>', 'test@example.com', 'bar@example.com']
        )


class SendNotificationTestCase(TestCase):
    def test_simple(self):
        job = self.create_job(self.project, result=Result.failed)
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

        job_link = 'http://example.com/builds/%s/' % (job.id.hex,)
        log_link = '%slogs/%s/' % (job_link, logsource.id.hex)

        send_notification(job, recipients=['foo@example.com', 'Bob <bob@example.com>'])

        assert len(self.outbox) == 1
        msg = self.outbox[0]

        assert msg.subject == 'Build Failed - %s (%s)' % (job.revision_sha, job.project.name)
        assert msg.recipients == ['foo@example.com', 'Bob <bob@example.com>']
        assert msg.extra_headers['Reply-To'] == 'foo@example.com, Bob <bob@example.com>'
        assert job_link in msg.html
        assert job_link in msg.body
        assert log_link in msg.html
        assert log_link in msg.body

        assert msg.as_string()


class GetLogClippingTestCase(TestCase):
    def test_simple(self):
        job = self.create_job(self.project)

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
