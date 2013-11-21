import mock

from changes.config import db
from changes.constants import Result
from changes.models import ProjectOption
from changes.listeners.mail import build_finished_handler, send_notification
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


class SendNotificationTestCase(TestCase):
    def test_simple(self):
        build = self.create_build(self.project, result=Result.failed)
        send_notification(build, recipients=['foo@example.com', 'Bob <bob@example.com>'])

        assert len(self.outbox) == 1
        msg = self.outbox[0]
        assert msg.subject == 'Build Failed - %s (%s)' % (build.revision_sha, build.project.name)
        assert msg.recipients == ['foo@example.com', 'Bob <bob@example.com>']
        assert msg.extra_headers['Reply-To'] == 'foo@example.com, Bob <bob@example.com>'
        build_link = 'http://example.com/builds/%s/' % (build.id.hex,)
        assert build_link in msg.html
        assert build_link in msg.body

        assert msg.as_string()
