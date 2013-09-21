import tornado.ioloop

from tornado.web import Application, url

from buildbox.conf import settings
from buildbox.web.frontend.build_list import BuildListHandler
from buildbox.web.frontend.build_details import BuildDetailsHandler


application = Application(
    [
        url(r"/", BuildListHandler,
            name='build-list'),
        url(r"/projects/([^/]+)/build/([^/]+)/", BuildDetailsHandler,
            name='build-details'),
    ],
    static_path=settings['static_path'],
    template_path=settings['template_path'],
    debug=settings['debug'],
)


if __name__ == "__main__":
    application.listen(7777)
    tornado.ioloop.IOLoop.instance().start()
