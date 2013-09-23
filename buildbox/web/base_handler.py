import tornado.web

from buildbox.db.backend import Backend


class BaseRequestHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        return Backend.instance()
