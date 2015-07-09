import json

from base64 import urlsafe_b64encode, urlsafe_b64decode
from functools import wraps
from urllib import quote

from flask import Response, request

from flask.ext.restful import Resource

from changes.api.serializer import serialize as serialize_func
from changes.config import db
from changes.config import statsreporter

from time import time

LINK_HEADER = '<{uri}&page={page}>; rel="{name}"'


def as_json(context):
    return json.dumps(serialize_func(context))


def error(message, problems=None, http_code=400):
    """ Returns a new error response to send API clients.

    :param message: A human readable description of the error
    :param problems: List of fields that caused the error.
    :param http_code: The HTTP code to use for the response.
    """
    error_response = {'error': message}
    if problems:
        error_response['problems'] = problems
    return error_response, http_code


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

    def __init__(self, *args, **kwargs):
        super(APIView, self).__init__(*args, **kwargs)

        self.start_time = 0  # used for logging performance stats

    def dispatch_request(self, *args, **kwargs):

        self.start_time = time()

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

    def cursor_paginate(self, queryset, id_func=lambda e: e.id, **kwargs):
        """
        Paginates results using a cursor:
          next page url: ?after=<id_of_last_elem>
          previous page url: ?before=<id_of_first_elem>
        This is more stable than offset pagination, especially for real-time
        datasets (people can share static links to builds, for example.)

        queryset: all the data (seems kind of inefficient...)
        id_func (function): maps a single queryset entry to a unique id used
        for pagination.
        **kwargs:
          fake_request (dict): used by unittest code: items within it
                               override request.args
          all other kwargs are passed directly to self.respond
        """

        my_request_args = request.args.copy()
        if 'fake_request' in kwargs:
            my_request_args.update(kwargs['fake_request'])
            del kwargs['fake_request']

        after = my_request_args.get('after')
        before = my_request_args.get('before')

        # TODO: don't crash if this isn't a number?
        per_page = int(my_request_args.get('per_page', 25))

        # per_page=0 means unlimited: don't paginate
        if per_page == 0:
            return self.respond(queryset, **kwargs)

        start_pos = None
        stop_pos = None
        if after and before:
            return "Paging Error: cannot pass both after and before as args!", 400
        elif after or before:
            # used for error message strings
            which_token = "after" if after else "before"

            encoded_item_id = after if after else before
            item_id = urlsafe_b64decode(str(encoded_item_id))

            if not item_id:
                return "Paging Error: %s has an invalid value!" % (which_token), 400

            position = next(
                (idx for idx, e in enumerate(queryset)
                 if id_func(e) == item_id),
                -1
            )

            if position == -1:
                return "Paging Error: could not find %s token in list!" % (which_token), 400
            elif position == len(queryset) - 1 and after:
                return "Paging Error: cannot get values after the last element!", 400
            # if position == 0 and before, fall through to the code below
            # (which will just return the first page)

            links = None
            if before:
                # the behavior is if per_page is 5 and you request elements
                # before item #3, we'll return the first 5 elements. I think
                # this is the most natural thing to do (note that after doesn't
                # do this, which is also natural IMO)
                start_pos = max(0, position - per_page)
                stop_pos = start_pos + per_page
            else:
                start_pos = position + 1
                # may be greater than len(queryset)
                stop_pos = position + 1 + per_page

        else:
            # neither after nor before: the user is on the first page and
            # hasn't paginated yet
            start_pos = 0
            stop_pos = per_page

        page_of_results = queryset[start_pos:stop_pos]
        links = self.make_cursor_links(
            id_func(queryset[start_pos]) if start_pos > 0 else None,
            id_func(queryset[stop_pos - 1]) if stop_pos < len(queryset) else None,
        )
        return self.respond(page_of_results, links=links, **kwargs)

    def make_cursor_links(self, before_id=None, after_id=None):
        """
        Creates the next/previous links using a specific format. Will
        not create a previous link if before_id is None (same with after_id)
        """

        # create base url to add pagination to
        querystring = u'&'.join(
            u'{0}={1}'.format(quote(k), quote(v))
            for k, v in request.args.iteritems()
            if (k != 'before' and k != 'after')
        )

        if querystring:
            base_url = '{0}?{1}&'.format(request.base_url, querystring)
        else:
            base_url = request.base_url + '?'

        # create links
        link_template = '<{uri}{pointer}={encoded_id}>; rel="{name}"'
        links = []
        if before_id:
            links.append(link_template.format(
                uri=base_url,
                pointer='before',
                encoded_id=urlsafe_b64encode(before_id),
                name='previous',
            ))

        if after_id:
            links.append(link_template.format(
                uri=base_url,
                pointer='after',
                encoded_id=urlsafe_b64encode(after_id),
                name='next',
            ))

        return links

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
        response.headers['changes-api-class'] = self.__class__.__name__

        timer_name = "changes_api_server_perf_method_{}_class_{}".format(
            request.method, self.__class__.__name__)
        time_taken = time() - self.start_time
        statsreporter.stats().log_timing(timer_name, time_taken * 1000)
        response.headers['changes-server-time'] = time_taken

        return response

    def serialize(self, *args, **kwargs):
        return serialize_func(*args, **kwargs)
