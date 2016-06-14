from __future__ import absolute_import, division, unicode_literals

from changes.api.auth import get_current_user
from changes.api.base import APIView


class AuthIndexAPIView(APIView):
    def get(self):
        """
        Return information on the currently authenticated user.
        """
        user = get_current_user()

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
