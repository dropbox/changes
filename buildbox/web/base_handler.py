import simplejson as json
import tornado.web

from buildbox.app import db


class BaseRequestHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        return db


class BaseAPIRequestHandler(BaseRequestHandler):
    def transform(self, value):
        if isinstance(value, dict):
            return {k: self.transform(v) for k, v in value.iteritems()}
        elif isinstance(value, (list, tuple, set, frozenset)):
            return [self.transform(v) for v in value]
        elif hasattr(value, 'to_dict'):
            return self.transform(value.to_dict())
        return value

    def as_json(self, context):
        return json.dumps(self.transform(context))

    def respond(self, context):
        self.set_header("Content-Type", "application/json")
        self.write(self.as_json(context))
