from __future__ import absolute_import, division, unicode_literals

from flask import session

from sqlalchemy.orm import joinedload

from changes.api.base import APIView
from changes.models import User, AdminMessage

import logging


class InitialIndexAPIView(APIView):
    def get(self):
        """
        Returns basic information used by every page:
          - is the user authenticated?
          - user messages
        """

        # authentication
        user = None
        if session.get('uid'):
            user = User.query.get(session['uid'])
            if user is None:
                del session['uid']

        auth = {
            'authenticated': False,
        }
        if user:
            auth = {
                'authenticated': True,
                'user': user,
            }

        # admin message
        messages = list(AdminMessage.query.options(
            joinedload('user'),
        ))

        admin_message = None
        if messages:
            if len(messages) > 1:
                # In the future we may have more than one message
                logging.warning('Multiple messages found')
            else:
                admin_message = messages[0]

        return self.respond({
            'auth': auth,
            'admin_message': admin_message
        })
