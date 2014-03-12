from __future__ import absolute_import

from datetime import datetime, timedelta

from changes.api.base import APIView
from changes.models import Node, JobStep


class NodeIndexAPIView(APIView):
    def get(self):
        cutoff = datetime.utcnow() - timedelta(days=7)

        queryset = Node.query.join(
            JobStep, JobStep.node_id == Node.id,
        ).filter(
            JobStep.date_created > cutoff,
        ).order_by(Node.label.asc()).group_by(Node)

        print queryset

        return self.paginate(queryset)
