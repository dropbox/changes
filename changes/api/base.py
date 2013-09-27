import json

from flask import Response
from flask.views import MethodView


def serialize(value):
    if isinstance(value, dict):
        return {k: serialize(v) for k, v in value.iteritems()}
    elif isinstance(value, (list, tuple, set, frozenset)):
        return [serialize(v) for v in value]
    elif hasattr(value, 'to_dict'):
        return serialize(value.to_dict())
    return value


def as_json(context):
    return json.dumps(serialize(context))


class APIView(MethodView):
    def respond(self, context):
        return Response(as_json(context), mimetype='application/json')
