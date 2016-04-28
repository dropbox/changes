from __future__ import absolute_import

from changes.api.base import APIView
from changes.models.node import Cluster, Node


class ClusterDetailsAPIView(APIView):
    def get(self, cluster_id):
        cluster = Cluster.query.get(cluster_id)
        if cluster is None:
            return '', 404

        node_count = Node.query.filter(
            Node.clusters.contains(cluster),
        ).count()

        context = self.serialize(cluster)
        context['numNodes'] = node_count

        return self.respond(context, serialize=False)
