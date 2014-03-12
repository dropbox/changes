from __future__ import absolute_import

from datetime import datetime, timedelta
from flask.ext.restful import reqparse

from changes.api.base import APIView
from changes.models import Node, JobStep


class NodeIndexAPIView(APIView):
    parser = reqparse.RequestParser()
    parser.add_argument('since', type=int, location='args')

    def get(self):
        args = self.parser.parse_args()
        if args.since:
            cutoff = datetime.utcnow() - timedelta(days=args.since)

            queryset = Node.query.join(
                JobStep, JobStep.node_id == Node.id,
            ).filter(
                JobStep.date_created > cutoff,
            ).group_by(Node)
        else:
            queryset = Node.query

        queryset = queryset.order_by(Node.label.asc())

        return self.paginate(queryset)
