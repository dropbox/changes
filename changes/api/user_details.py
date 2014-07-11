from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful import reqparse

from changes.api.auth import requires_admin
from changes.api.base import APIView
from changes.config import db
from changes.models import User


class UserDetailsAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('is_admin', type=lambda x: bool(int(x)))

    def get(self, user_id):
        user = User.query.get(user_id)
        if user is None:
            return '', 404

        return self.respond(user)

    @requires_admin
    def post(self, user_id):
        user = User.query.get(user_id)
        if user is None:
            return '', 404

        args = self.parser.parse_args()

        if args.is_admin is not None:
            user.is_admin = args.is_admin

        db.session.add(user)
        db.session.commit()

        return self.respond(user)
