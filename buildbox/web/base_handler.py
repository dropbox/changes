import tornado.web

from buildbox.db.backend import Backend
from buildbox.constants import Status, Result


def get_enum_label_func(cls):
    def newfunc(value):
        return str(value)
    return newfunc


class BaseRequestHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        return Backend.instance()

    def render(self, *args, **kwargs):
        kwargs['get_status_label'] = get_enum_label_func(Status)
        kwargs['get_result_label'] = get_enum_label_func(Result)

        return super(BaseRequestHandler, self).render(*args, **kwargs)
