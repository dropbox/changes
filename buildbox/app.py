from sqlalchemy import create_engine
from tornado.web import url
from tornadoredis import Client

from buildbox.config import settings
from buildbox.db.backend import Backend

db = Backend(create_engine(
    settings['database'],
    # pool_size=options.mysql_poolsize,
    # pool_recycle=3600,
    # echo=settings['debug'],
    # echo_pool=settings['debug'],
))

redis = Client()

from buildbox.server import BuildboxServer
from buildbox.web.api.build_list import BuildListApiHandler
from buildbox.web.api.stream import StreamHandler, TestStreamHandler
from buildbox.web.frontend.build_list import BuildListHandler
from buildbox.web.frontend.build_details import BuildDetailsHandler

application = BuildboxServer(
    [
        url(r"/", BuildListHandler,
            name='build-list'),
        url(r"/projects/([^/]+)/build/([^/]+)/", BuildDetailsHandler,
            name='build-details'),

        url(r"/api/0/stream/", StreamHandler,
            name='api-stream'),
        url(r"/api/0/stream/test/", TestStreamHandler,
            name='api-stream-team'),
        url(r"/api/0/builds/", BuildListApiHandler,
            name='api-build-list'),
    ],
    static_path=settings['static_path'],
    template_path=settings['template_path'],
    debug=settings['debug'],
)
