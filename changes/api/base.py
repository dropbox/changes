import gevent
import json

from collections import deque
from functools import wraps

from flask import Response, current_app as app, request
from flask.views import MethodView

from changes.config import pubsub
from changes.api.serializer import serialize


def as_json(context):
    return json.dumps(serialize(context))


def param(key, validator=lambda x: x, required=True, dest=None):
    def wrapped(func):
        @wraps(func)
        def _wrapped(*args, **kwargs):
            if key in kwargs:
                value = kwargs.pop(key, '')
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


class EventStream(object):
    def __init__(self, channels, pubsub=pubsub):
        self.pubsub = pubsub
        self.pending = deque()
        self.channels = channels
        self.active = True

        for channel in channels:
            self.pubsub.subscribe(channel, self.push)

    def __iter__(self):
        while self.active:
            # TODO(dcramer): figure out why we have to send this to ensure
            # the connection is opened
            yield "\n"
            while self.pending:
                event = self.pending.pop()
                yield "event: {}\n\n".format(event['event'])
                for line in event['data'].splitlines():
                    yield "data: {}\n".format(line)
                yield "\n"
                gevent.sleep(0)
            gevent.sleep(0.3)

    def __del__(self):
        self.close()

    def push(self, message):
        self.pending.append(message)

    def close(self):
        for channel in self.channels:
            self.pubsub.unsubscribe(channel, self.push)


class APIView(MethodView):
    def dispatch_request(self, *args, **kwargs):
        if 'text/event-stream' in request.headers.get('Accept', ''):
            channels = self.get_stream_channels(**kwargs)
            if not channels:
                return Response(status=404)
            return self.stream_response(channels)

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

    def as_json(self, context):
        return json.dumps(serialize(context))

    def get_stream_channels(self, **kwargs):
        return []

    def stream_response(self, channels):
        from flask import Response

        stream = EventStream(channels=channels)
        return Response(stream, mimetype='text/event-stream')
