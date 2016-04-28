from __future__ import absolute_import

import logging

from datetime import datetime
from flask import session
from flask.ext.restful import reqparse
from sqlalchemy.orm import joinedload

from changes.api.auth import requires_admin
from changes.api.base import APIView
from changes.db.utils import create_or_update
from changes.models.adminmessage import AdminMessage


class AdminMessageIndexAPIView(APIView):
    """ CRUD API for the AdminMessage model.

    AdminMessages are system-level messages that should be displayed to users.

    This API is intended for use by the Changes UI for displaying information
    about outages, upcoming down-time or new features. These messages can be
    fetched by anyone, but are intended to be set only by admins. That admin
    restriction for creating messages isn't a system requirement, but seems
    like a reasonable safety restriction.
    """

    post_parser = reqparse.RequestParser()
    post_parser.add_argument('message', type=unicode, required=True)

    def get(self):
        """ HTTP GET response to read AdminMessages.

        Returns:
            str: None if no messages are found; others JSON representation of
            the AdminMessage in the system. If the message is empty, treat that
            as no message.
        """
        messages = list(AdminMessage.query.options(
            joinedload('user'),
        ))

        if not messages:
            return self.respond(None)

        # In the future we may have more than one message
        if len(messages) > 1:
            logging.warning('Multiple messages found')

        return self.respond(messages[0])

    @requires_admin
    def post(self):
        """ HTTP POST to create or update AdminMessages.

        This API enforces that we only ever have at most one message. This will
        likely change in the future. To clear the current message, post an empty
        message. Messages cannot be deleted once created.

        Returns:
            str: JSON representation of the AdminMessage that was edited.
        """
        args = self.post_parser.parse_args()

        # Enforce we only ever have a single message
        message, _ = create_or_update(AdminMessage, where={}, values={
            'message': args.message,
            'user_id': session['uid'],
            'date_created': datetime.utcnow()
        })

        # Response isn't required, but we give one to make testing easier
        return self.respond(message)
