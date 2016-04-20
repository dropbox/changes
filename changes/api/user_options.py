from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful.reqparse import RequestParser

from changes.api.base import APIView, error
from changes.db.utils import create_or_update
from changes.models.option import ItemOption

from changes.api.auth import get_current_user


class UserOptionsAPIView(APIView):

    # get is not implemented...add functionality to initial_index instead if
    # needed

    post_parser = RequestParser()
    post_parser.add_argument('user.colorblind')

    def post(self):
        user = get_current_user()
        if user is None:
            return error("User not found", http_code=404)

        args = self.post_parser.parse_args()

        for name, value in args.iteritems():
            if value is None:
                continue

            create_or_update(ItemOption, where={
                'item_id': user.id,
                'name': name,
            }, values={
                'value': value,
            })

        return self.respond({})
