import inspect
import os.path
import sqlalchemy.engine
import sys

from flask import render_template
from time import time
from sqlalchemy.dialects import postgresql
from threading import local
from urlparse import parse_qs

ROOT = os.path.dirname(sys.modules['changes'].__file__)


class Event(object):
    def __init__(self, start_time, message, traceback=None, end_time=None):
        self.start_time = start_time
        self.message = message
        self.traceback = traceback
        self.end_time = end_time

    def __hash__(self):
        return hash([self.time, self.message])

    @property
    def duration(self):
        if not self.end_time:
            return 0
        return self.end_time - self.start_time


class Tracer(local):
    def __init__(self):
        super(Tracer, self).__init__()
        self.reset()

    def enable(self):
        self.active = True

    def reset(self):
        self.events = []
        self.active = False

    def start_event(self, message):
        __traceback_hide__ = True  # NOQA

        if not self.active:
            return

        event = Event(
            start_time=time(),
            message=message,
            traceback=self.get_traceback(),
        )
        self.events.append(event)
        return event

    def end_event(self, event):
        if not event:
            return
        event.end_time = time()

    def get_traceback(self):
        __traceback_hide__ = True  # NOQA

        result = []

        for frame, filename, lineno, function, code, _ in inspect.stack():
            f_locals = getattr(frame, 'f_locals', {})
            if '__traceback_hide__' in f_locals:
                continue
            # filename = frame.f_code.co_filename
            if not filename.startswith(ROOT):
                continue

            result.append(
                'File "{filename}", line {lineno}, in {function}\n{code}'.format(
                    function=function,
                    lineno=lineno,
                    code='\n'.join(code or '').rstrip('\n'),
                    filename=filename[len(ROOT) + 1:],
                )
            )
        return '\n'.join(result)

    def collect(self):
        return self.events


class SQLAlchemyTracer(object):
    def __init__(self, tracer):
        self.tracer = tracer
        self.reset()

    def reset(self):
        self.tracking = {}

    def install(self, engine=sqlalchemy.engine.Engine):
        sqlalchemy.event.listen(engine, "before_execute", self.before_execute)
        sqlalchemy.event.listen(engine, "after_execute", self.after_execute)

    def before_execute(self, conn, clause, multiparams, params):
        __traceback_hide__ = True  # NOQA

        query = unicode(clause.compile(dialect=postgresql.dialect()))
        self.tracking[(conn, clause)] = self.tracer.start_event(query)

    def after_execute(self, conn, clause, multiparams, params, results):
        __traceback_hide__ = True  # NOQA

        try:
            event = self.tracking.pop((conn, clause))
        except KeyError:
            return

        self.tracer.end_event(event)


class TracerMiddleware(object):
    def __init__(self, wsgi_app, app):
        self.tracer = Tracer()

        self.sqlalchemy_tracer = SQLAlchemyTracer(self.tracer)
        self.sqlalchemy_tracer.install()

        self.wsgi_app = wsgi_app
        self.app = app

    def __call__(self, environ, start_response):
        __traceback_hide__ = True  # NOQA

        # if we've passed ?trace and we're a capable request we show
        # our tracing report
        qs = parse_qs(environ.get('QUERY_STRING', ''), True)
        do_trace = '__trace__' in qs

        if not do_trace:
            return self.wsgi_app(environ, start_response)

        self.tracer.enable()

        iterable = None

        try:
            iterable = self.wsgi_app(environ, start_response)

            for event in iterable:
                event  # do nothing

            return self.report(environ, start_response)
        finally:
            if hasattr(iterable, 'close'):
                iterable.close()

            self.tracer.reset()
            self.sqlalchemy_tracer.reset()

    def report(self, environ, start_response):
        with self.app.request_context(environ):
            response = render_template('trace.html', events=self.tracer.collect())

        response = response.encode('utf-8')

        start_response('200 OK', [
            ('Content-Type', 'text/html'),
            ('Content-Length', str(len(response))),
        ])
        return iter([response])
