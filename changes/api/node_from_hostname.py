from __future__ import absolute_import

from changes.api.base import APIView, error
from changes.models.node import Node


class NodeFromHostnameAPIView(APIView):
    def get(self, node_hostname):
        node = Node.query.filter(Node.label == node_hostname).first()
        if node is None:
            return error("Node not found", http_code=404)

        context = self.serialize(node)
        context['clusters'] = self.serialize(list(node.clusters))

        return self.respond(context, serialize=False)
