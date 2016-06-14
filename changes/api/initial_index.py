from __future__ import absolute_import, division, unicode_literals

from sqlalchemy.orm import joinedload

from changes.api.auth import get_current_user
from changes.api.base import APIView
from changes.models.adminmessage import AdminMessage

import logging


class InitialIndexAPIView(APIView):
    def get(self):
        """
        Returns basic information used by every page:
          - is the user authenticated?
          - user messages
        """

        # authentication
        user = get_current_user()
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
