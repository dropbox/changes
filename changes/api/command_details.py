from __future__ import absolute_import

from datetime import datetime
from flask_restful.reqparse import RequestParser

from changes.api.base import APIView
from changes.api.validators.datetime import ISODatetime
from changes.config import db
from changes.constants import Status
from changes.models import Command


STATUS_CHOICES = ('queued', 'in_progress', 'finished')


class CommandDetailsAPIView(APIView):
    post_parser = RequestParser()
    post_parser.add_argument('status', choices=STATUS_CHOICES)
    post_parser.add_argument('return_code', type=int)
    post_parser.add_argument('date', type=ISODatetime())

    def get(self, command_id):
        command = Command.query.get(command_id)
        if command is None:
            return '', 404

        return self.respond(command)

    def post(self, command_id):
        command = Command.query.get(command_id)
        if command is None:
            return '', 404

        args = self.post_parser.parse_args()

        current_datetime = args.date or datetime.utcnow()

        if args.return_code is not None:
            command.return_code = args.return_code

        if args.status:
            command.status = Status[args.status]

            # if we've finished this job, lets ensure we have set date_finished
            if command.status == Status.finished and command.date_finished is None:
                command.date_finished = current_datetime
            elif command.status != Status.finished and command.date_finished:
                command.date_finished = None

            if command.status != Status.queued and command.date_started is None:
                command.date_started = current_datetime
            elif command.status == Status.queued and command.date_started:
                command.date_started = None

        db.session.add(command)
        db.session.commit()

        return self.respond(command)
