from flask import _app_ctx_stack


class ContainerState(object):
    def __init__(self, app, callback, options):
        self.app = app
        self.instance = callback(app, options)

    def __getattr__(self, name):
        return getattr(self.instance, name)


class ContainerMethod(object):
    """
    Proxies a method to an extension allowing us to bind the result
    to the correct application state.
    """
    def __init__(self, ext, name):
        self.ext = ext
        self.name = name

    def __call__(self, *args, **kwargs):
        state = self.ext.get_state()
        return getattr(state, self.name)(*args, **kwargs)


class Container(object):
    """
    Creates an extension container for app-bound execution of an object.

    >>> redis = Container(
    >>>     lambda app, kwargs: redis.StrictClient(**kwargs),
    >>>     {'host': 'localhost'})
    """
    def __init__(self, callback, options=None, name=None):
        self.callback = callback
        self.options = options or {}
        self.ident = name or id(self)
        self.app = None

    def __getattr__(self, name):
        state = self.get_state()
        attr = getattr(state, name)
        if callable(attr):
            method = ContainerMethod(self, name)
            method.__name__ = name
            method.__doc__ = name.__doc__
            return method
        return attr

    def init_app(self, app):
        self.app = app
        if not hasattr(app, 'extensions'):
            app.extensions = {}
        app.extensions[self.ident] = ContainerState(
            app=app,
            callback=self.callback,
            options=self.options,
        )

    def get_state(self, app=None):
        """Gets the state for the application"""
        if app is None:
            app = self.get_app()
        assert self.ident in app.extensions, \
            'The extension was not registered to the current ' \
            'application.  Please make sure to call init_app() first.'
        return app.extensions[self.ident]

    def get_app(self, reference_app=None):
        if reference_app is not None:
            return reference_app
        if self.app is not None:
            return self.app
        ctx = _app_ctx_stack.top
        if ctx is not None:
            return ctx.app
        raise RuntimeError('application not registered on '
                           'instance and no application bound '
                           'to current context')
