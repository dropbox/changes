import json

from functools import wraps

from flask import Response, current_app as app, request
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


def param(key, validator=lambda x: x, required=True, dest=None):
    def wrapped(func):
        @wraps(func)
        def _wrapped(*args, **kwargs):
            if key in kwargs:
                value = kwargs[key] or ''
            elif request.method == 'POST':
                value = request.form.get(key) or ''
            else:
                value = ''

            dest_key = str(dest or key)

            value = value.strip()
            if not value:
                if required:
                    raise ParamError(key, 'value is required')
                kwargs[dest_key] = value
                return func(*args, **kwargs)

            try:
                value = validator(value)
            except ParamError:
                raise
            except Exception:
                raise ParamError(key, 'invalid value')

            kwargs[dest_key] = value

            return func(*args, **kwargs)

        return _wrapped
    return wrapped


class APIError(Exception):
    pass


class ParamError(APIError):
    def __init__(self, key, msg):
        self.key = key
        self.msg = msg

    def __unicode__(self):
        return '{0} is not valid: {1}'.format(self.key, self.msg)


class APIView(MethodView):
    def dispatch_request(self, *args, **kwargs):
        try:
            return super(APIView, self).dispatch_request(*args, **kwargs)
        except APIError as exc:
            app.logger.info(unicode(exc), exc_info=True)
            return self.respond({
                'message': unicode(exc),
            }, status_code=403)
        except Exception as exc:
            app.logger.exception(unicode(exc))
            return self.respond({
                'message': 'Internal error',
            }, status_code=500)

    def respond(self, context, status_code=200):
        return Response(
            as_json(context),
            mimetype='application/json',
            status=status_code)
