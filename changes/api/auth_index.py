from __future__ import absolute_import, division, unicode_literals

from flask import session

from changes.api.base import APIView
from changes.models import User


class AuthIndexAPIView(APIView):
    def get(self):
        """
        Return information on the currently authenticated user.
        """
        if session.get('uid'):
            user = User.query.get(session['uid'])
            if user is None:
                del session['uid']
        else:
            user = None

        if user is None:
            context = {
                'authenticated': False,
            }
        else:
            context = {
                'authenticated': True,
                'user': user,
            }

        return self.respond(context)
