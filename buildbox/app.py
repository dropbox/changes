import tornado.ioloop
import tornado.web

from buildbox.conf import settings
from buildbox.web.frontend import BuildDetailsHandler


application = tornado.web.Application(
    [
        (r"/projects/(\d+)/build/(\d+)/", BuildDetailsHandler),
    ],
    static_path=settings['static_path'],
    template_path=settings['template_path'],
    debug=settings['debug'],
)


if __name__ == "__main__":
    application.listen(7777)
    tornado.ioloop.IOLoop.instance().start()
