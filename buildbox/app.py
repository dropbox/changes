import os.path

from sqlalchemy import create_engine
from tornado.web import url, StaticFileHandler
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
from buildbox.web.api.build_details import BuildDetailsApiHandler
from buildbox.web.api.build_list import BuildListApiHandler
from buildbox.web.api.stream import StreamHandler, TestStreamHandler
from buildbox.web.frontend.index import IndexHandler

application = BuildboxServer(
    [
        url(r"/", IndexHandler,
            name='index'),

        url(r"/api/0/stream/", StreamHandler,
            name='api-stream'),
        url(r"/api/0/stream/test/", TestStreamHandler,
            name='api-stream-team'),
        url(r"/api/0/builds/", BuildListApiHandler,
            name='api-build-list'),
        url(r"/api/0/builds/([^/]+)/", BuildDetailsApiHandler,
            name='api-build-details'),

        url(r'/(.*)', StaticFileHandler, {
            'path': settings['www_root'],
        }),

    ],
    static_path=settings['static_path'],
    template_path=settings['template_path'],
    debug=settings['debug'],
)
