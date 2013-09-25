import simplejson as json
import tornado.web

from buildbox.db.backend import Backend


class BaseRequestHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        return Backend.instance()


class APIRequestHandler(BaseRequestHandler):
    def transform(self, value):
        if isinstance(value, dict):
            return {k: self.transform(v) for k, v in value.iteritems()}
        elif isinstance(value, (list, tuple, set, frozenset)):
            return [self.transform(v) for v in value]
        elif hasattr(value, 'to_dict'):
            return self.transform(value.to_dict())
        return value

    def respond(self, context):
        self.set_header("Content-Type", "application/json")
        self.write(json.dumps(self.transform(context)))
