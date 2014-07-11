from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful.reqparse import RequestParser

from changes.api.base import APIView
from changes.api.auth import requires_admin
from changes.db.utils import create_or_update
from changes.models import SystemOption


OPTION_DEFAULTS = {
    'system.message': '',
}


class SystemOptionsAPIView(APIView):
    def get(self):
        options = dict(
            (o.name, o.value) for o in SystemOption.query.all()
        )
        for key, value in OPTION_DEFAULTS.iteritems():
            options.setdefault(key, value)

        return self.respond(options)

    post_parser = RequestParser()
    for option in OPTION_DEFAULTS.keys():
        post_parser.add_argument(option)

    @requires_admin
    def post(self):
        args = self.post_parser.parse_args()

        for name, value in args.iteritems():
            if value is None:
                continue

            create_or_update(SystemOption, where={
                'name': name,
            }, values={
                'value': value,
            })

        return '', 200
