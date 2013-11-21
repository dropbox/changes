from changes.constants import Result
from changes.listeners.mail import build_finished_handler
from changes.testutils.cases import TestCase


class BuildFinishedHandlerTestCase(TestCase):
    def test_simple(self):
        # test without an author
        build = self.create_build(self.project, result=Result.failed, author=None)
        build_finished_handler(build)

        assert len(self.outbox) == 0

        # not failing
        author = self.create_author('foo@example.com')
        build = self.create_build(self.project, result=Result.passed, author=author)

        assert len(self.outbox) == 0

        # all conditions should apply truthfully
        build = self.create_build(self.project, result=Result.failed, author=author)
        build_finished_handler(build)

        assert len(self.outbox) == 1
        msg = self.outbox[0]
        assert msg.subject == 'Build Failed - %s (%s)' % (build.revision_sha, build.project.name)
        assert msg.recipients == ['foo@example.com']
        assert msg.cc == ['foo@example.com']
        build_link = 'http://example.com/builds/%s/' % (build.id.hex,)
        assert build_link in msg.html_body
        assert build_link in msg.body
