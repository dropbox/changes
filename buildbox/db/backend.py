from sqlalchemy.orm import sessionmaker


class Backend(object):
    def __init__(self, engine=None):
        from buildbox.app import application

        if engine is None:
            engine = application.settings['sqla_engine']

        self.engine = engine

    @classmethod
    def instance(cls):
        if not hasattr(cls, '_instance'):
            cls._instance = cls()
        return cls._instance

    @property
    def connection(self):
        if not hasattr(self, '_connection'):
            self._connection = self.engine.connect()
        return self._connection

    def create_session(self, *args, **kwargs):
        if not hasattr(self, '_sessionmaker'):
            self._sessionmaker = sessionmaker(bind=self.connection)
        return self._sessionmaker(*args, **kwargs)

    def get_session(self):
        return SessionContextManager(self)


# TODO(cramer): this is likely blocking the Tornado ioloop
class SessionContextManager(object):
    def __init__(self, backend):
        self.backend = backend

    def __enter__(self):
        self.session = self.backend.create_session(expire_on_commit=False)
        return self.session

    def __exit__(self, *exc_info):
        self.session.commit()
        self.session.expunge_all()
        self.session.close()
