from sqlalchemy.orm import sessionmaker

from .async import AsyncConnectionManager


class Backend(object):
    def __init__(self, engine=None):
        from buildbox.app import application

        if engine is None:
            engine = application.settings['sqla_engine']
        self.create_session = sessionmaker(bind=engine)
        # TODO: should we bind concurrency to the number of connections
        # available in the pool?
        self.conn_manager = AsyncConnectionManager()

    @classmethod
    def instance(cls):
        """Singleton like accessor to instantiate backend object"""
        if not hasattr(cls, "_instance"):
            cls._instance = cls()
        return cls._instance

    def get_session(self):
        return SessionContextManager(self)


class SessionContextManager(object):
    def __init__(self, backend):
        self.backend = backend

    def __enter__(self):
        self.session = self.backend.create_session()
        return self.session

    def __exit__(self, *exc_info):
        yield self.backend.conn_manager.commit(self.session)
