import tornado.web

from changes.app import db


class BaseRequestHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        return db
