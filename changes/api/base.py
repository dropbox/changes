import json

from functools import wraps
from urllib import quote

from flask import Response, request
from flask.ext.restful import Resource

from changes.api.serializer import serialize as serialize_func
from changes.config import db

LINK_HEADER = '<{uri}&page={page}>; rel="{name}"'


def as_json(context):
    return json.dumps(serialize_func(context))


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


class APIView(Resource):
    def dispatch_request(self, *args, **kwargs):
        try:
            response = super(APIView, self).dispatch_request(*args, **kwargs)
        except Exception:
            db.session.rollback()
            raise
        else:
            db.session.commit()
        return response

    def paginate(self, queryset, max_per_page=100, **kwargs):
        page = int(request.args.get('page', 1))
        per_page = int(request.args.get('per_page', 25) or 0)
        if max_per_page:
            assert per_page <= max_per_page
        assert page > 0

        if per_page:
            offset = (page - 1) * per_page
            result = list(queryset[offset:offset + per_page + 1])
        else:
            offset = 0
            page = 1
            result = list(queryset)

        links = self.make_links(
            current_page=page,
            has_next_page=per_page and len(result) > per_page,
        )

        if per_page:
            result = result[:per_page]

        return self.respond(result, links=links, **kwargs)

    def make_links(self, current_page, has_next_page=None):
        links = []
        if current_page > 1:
            links.append(('previous', current_page - 1))

        if has_next_page:
            links.append(('next', current_page + 1))

        querystring = u'&'.join(
            u'{0}={1}'.format(quote(k), quote(v))
            for k, v in request.args.iteritems()
            if k != 'page'
        )
        if querystring:
            base_url = '{0}?{1}'.format(request.base_url, querystring)
        else:
            base_url = request.base_url + '?'

        link_values = []
        for name, page_no in links:
            link_values.append(LINK_HEADER.format(
                uri=base_url,
                page=page_no,
                name=name,
            ))
        return link_values

    def respond(self, context, status_code=200, serialize=True, serializers=None,
                links=None):
        if serialize:
            data = self.serialize(context, serializers)
        else:
            data = context

        response = Response(
            as_json(data),
            mimetype='application/json',
            status=status_code,
        )

        if links:
            response.headers['Link'] = ', '.join(links)

        return response

    def serialize(self, *args, **kwargs):
        return serialize_func(*args, **kwargs)

    def as_json(self, context):
        return json.dumps(context)
