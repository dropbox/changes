from __future__ import absolute_import

from changes.api.base import APIView
from changes.models import Node


class NodeIndexAPIView(APIView):
    def get(self):
        queryset = Node.query.order_by(Node.label.asc())

        return self.paginate(queryset)
