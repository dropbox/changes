import tornado.web

from buildbox.app import db


class BaseRequestHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        return db
