from sqlalchemy import create_engine
from tornado.web import Application, url

from buildbox.config import settings
from buildbox.db.backend import Backend
from buildbox.web.api.build_list import BuildListApiHandler
from buildbox.web.frontend.build_list import BuildListHandler
from buildbox.web.frontend.build_details import BuildDetailsHandler


application = Application(
    [
        url(r"/", BuildListHandler,
            name='build-list'),
        url(r"/projects/([^/]+)/build/([^/]+)/", BuildDetailsHandler,
            name='build-details'),

        url(r"/api/0/builds/", BuildListApiHandler,
            name='api-build-list'),
    ],
    static_path=settings['static_path'],
    template_path=settings['template_path'],
    debug=settings['debug'],
    sqla_engine=create_engine(
        settings['database'],
        # pool_size=options.mysql_poolsize,
        # pool_recycle=3600,
        # echo=settings['debug'],
        # echo_pool=settings['debug'],
    ),
)

db = Backend.instance()
