from __future__ import absolute_import

from changes.api.base import APIView
from changes.models import Node


class NodeDetailsAPIView(APIView):
    def get(self, node_id):
        node = Node.query.get(node_id)
        if node is None:
            return '', 404

        return self.respond(node)
