import sqlalchemy.engine
import traceback

from flask import render_template
from time import time
from threading import local
from urlparse import parse_qs


class Tracer(local):
    def __init__(self):
        super(Tracer, self).__init__()
        self.reset()

    def enable(self):
        self.active = True

    def reset(self):
        self.events = []
        self.active = False

    def add_event(self, message, duration=None):
        if self.active:
            self.events.append((
                time(),
                unicode(message),
                duration,
                ''.join(traceback.format_stack())
            ))

    def collect(self):
        return self.events


class SQLAlchemyTracer(object):
    def __init__(self, tracer):
        self.tracking = {}
        self.tracer = tracer

    def install(self, engine=sqlalchemy.engine.Engine):
        sqlalchemy.event.listen(engine, "before_execute", self.before_execute)
        sqlalchemy.event.listen(engine, "after_execute", self.after_execute)

    def before_execute(self, conn, clause, multiparams, params):
        self.tracking[(conn, clause)] = time()

    def after_execute(self, conn, clause, multiparams, params, results):
        start_time = self.tracking.pop((conn, clause))
        if start_time:
            duration = time() - start_time
        else:
            duration = None
        self.tracer.add_event(clause, duration)


class TracerMiddleware(object):
    def __init__(self, wsgi_app, app):
        self.tracer = Tracer()

        self.sqlalchemy_tracer = SQLAlchemyTracer(self.tracer)
        self.sqlalchemy_tracer.install()

        self.wsgi_app = wsgi_app
        self.app = app

    def __call__(self, environ, start_response):
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

    def report(self, environ, start_response):
        start_response('200 OK', [('Content-Type', 'text/html')])

        with self.app.request_context(environ):
            return render_template('trace.html', events=self.tracer.collect())
