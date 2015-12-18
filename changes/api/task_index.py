from __future__ import absolute_import

from flask_restful.reqparse import RequestParser

from changes.api.base import APIView
from changes.models.task import Task

import uuid


class TaskIndexAPIView(APIView):
    get_parser = RequestParser()

    # If specified, the results will be limited to Tasks associated with this object id.
    get_parser.add_argument('object_id', type=uuid.UUID, default=None)

    def get(self):
        args = self.get_parser.parse_args()

        queryset = Task.query.order_by(Task.date_created.desc())
        if args.object_id:
            queryset = queryset.filter(Task.task_id == args.object_id)

        return self.paginate(queryset)
