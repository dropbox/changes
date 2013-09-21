import os.path
import tornado.ioloop
import tornado.web

from buildbox.web.frontend import BuildDetailsHandler

root = os.path.abspath(os.path.dirname(__file__))


config = {
    'static_path': os.path.join(root, 'static'),
    'template_path': os.path.join(root, 'templates'),
    'debug': True,
}

application = tornado.web.Application([
    (r"/projects/(\d+)/build/(\d+)/", BuildDetailsHandler),
], **config)

if __name__ == "__main__":
    application.listen(7777)
    tornado.ioloop.IOLoop.instance().start()
