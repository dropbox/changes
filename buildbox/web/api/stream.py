import tornado.web
import tornado.gen

from buildbox.web.base_handler import BaseAPIRequestHandler


class StreamHandler(BaseAPIRequestHandler):
    @tornado.web.asynchronous
    def get(self):
        self.set_header("Content-Type", "text/event-stream")
        self.set_header("Cache-Control", "no-cache")
        self.flush()
        self.application.subscribe('builds', self.on_message)

    def on_message(self, message):
        self.write("data: %s\n\n" % (message,))
        self.flush()


class TestStreamHandler(BaseAPIRequestHandler):
    def get(self):
        from datetime import datetime
        from buildbox.constants import Result, Status
        from buildbox.models import Build, Project, Author

        with self.db.get_session() as session:
            project = session.query(Project).all()[0]
            author = session.query(Author).all()[0]

        self.application.publish('builds', self.as_json(Build(
            label='Test Build',
            project=project,
            author=author,
            status=Status.in_progress,
            result=Result.unknown,
            date_created=datetime.utcnow(),
            date_started=datetime.utcnow(),
        )))
