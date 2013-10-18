import redis
import rq

from flask import _app_ctx_stack


def get_state(app):
    """Gets the state for the application"""
    assert 'queue' in app.extensions, \
        'The queue extension was not registered to the current ' \
        'application.  Please make sure to call init_app() first.'
    return app.extensions['queue']


class _QueueState(object):
    def __init__(self, ext, app):
        self.ext = ext
        self.app = app

    def get_connection(self, queue='default'):
        return redis.from_url(self.app.config['REDIS_URL'])

    def get_queue(self, name='default', **kwargs):
        kwargs['connection'] = self.get_connection(name)
        return rq.Queue(name, **kwargs)

    def get_server_url(self, name):
        return self.app.config['REDIS_URL']

    def get_worker(self, *queues, **config):
        if len(queues) == 0:
            queues = ['default']

        connection = config.pop('connection', None)
        if connection is None:
            connection = self.get_connection(queues[0])

        config.setdefault('default_result_ttl', self.app.config['RQ_DEFAULT_RESULT_TTL'])
        servers = [self.get_server_url(name) for name in queues]

        if not servers.count(servers[0]) == len(servers):
            raise Exception('A worker only accept one connection')

        return rq.Worker(
            [self.get_queue(name) for name in queues],
            connection=connection,
            **config
        )


class Queue(object):
    def __init__(self, app=None):
        self.app = None

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.app = app

        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions['queue'] = _QueueState(self, app)

    def get_app(self, reference_app=None):
        if reference_app is not None:
            return reference_app
        if self.app is not None:
            return self.app
        ctx = _app_ctx_stack.top
        if ctx is not None:
            return ctx.app
        raise RuntimeError('application not registered on db '
                           'instance and no application bound '
                           'to current context')

    def get_queue(self, *args, **kwargs):
        return self.get_app().extensions['queue'].get_queue(*args, **kwargs)

    def get_worker(self, *args, **config):
        return self.get_app().extensions['queue'].get_worker(*args, **config)

    def job(self, func_or_queue=None):
        if callable(func_or_queue):
            func = func_or_queue
            queue = 'default'
        else:
            func = None
            queue = func_or_queue

        def wrapper(fn):
            from flask import current_app

            def delay(*args, **kwargs):
                q = current_app.extensions['queue'].get_queue(queue)
                return q.enqueue(fn, *args, **kwargs)

            fn.delay = delay
            return fn

        if func is not None:
            return wrapper(func)

        return wrapper
