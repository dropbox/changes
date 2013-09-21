from ..conf import settings

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


class Backend(object):
    def __init__(self):
        engine = create_engine(
            settings['database'],
            # pool_size=options.mysql_poolsize,
            # pool_recycle=3600,
            echo=settings['debug'],
            echo_pool=settings['debug'],
        )
        self._session = sessionmaker(bind=engine)

    @classmethod
    def instance(cls):
        """Singleton like accessor to instantiate backend object"""
        if not hasattr(cls, "_instance"):
            cls._instance = cls()
        return cls._instance

    def get_session(self):
        return self._session()
