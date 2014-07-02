from changes.config import db
from changes.models import LogSource, LogChunk
from changes.listeners.notification_base import NotificationHandler
from changes.testutils.cases import TestCase


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

        handler = NotificationHandler()
        result = handler.get_log_clipping(logsource, max_size=200, max_lines=3)
        assert result == "world\r\nhello\r\nworld"

        result = handler.get_log_clipping(logsource, max_size=200, max_lines=1)
        assert result == "world"

        result = handler.get_log_clipping(logsource, max_size=5, max_lines=3)
        assert result == "world"
